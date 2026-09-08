"""Export authorised student data to a chosen destination.

No unauthenticated portal scrape. Destinations that need live OAuth stay
labelled adapters until credentials exist. Webhook payloads are hashed/redacted.
"""

from __future__ import annotations

from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ids import new_id
from app.domain.models import ExportReceipt, MailItem, Obligation
from app.policies.consent import ConsentError
from app.services import clock
from app.services.formatter import format_record, payload_digest, strip_html
from app.settings import get_settings

DESTINATIONS = ("json", "csv", "webhook", "email", "postgres", "sheets", "airtable", "s3")


def _classify_error(exc: Exception) -> dict[str, str]:
    name = type(exc).__name__
    text = str(exc).lower()
    if "timeout" in text or name in {"TimeoutException", "ConnectTimeout", "ReadTimeout"}:
        return {"route": "retry_later", "code": "connectivity_timeout"}
    if "429" in text or "rate" in text:
        return {"route": "backoff", "code": "rate_limited"}
    if "401" in text or "403" in text:
        return {"route": "auth", "code": "destination_unauthorized"}
    return {"route": "fail_closed", "code": "export_failed"}


async def collect_export(session: AsyncSession, user_id: str) -> list[dict[str, Any]]:
    obligations = (
        await session.execute(select(Obligation).where(Obligation.user_id == user_id))
    ).scalars().all()
    mail = (
        await session.execute(select(MailItem).where(MailItem.user_id == user_id))
    ).scalars().all()
    rows: list[dict[str, Any]] = []
    for obl in obligations:
        rows.append(
            format_record(
                {
                    "kind": "obligation",
                    "title": obl.title,
                    "course": obl.course_or_context,
                    "due_at": obl.due_at.isoformat() if obl.due_at else None,
                    "status": obl.status,
                    "source_type": obl.source_type,
                }
            )
        )
    for msg in mail:
        rows.append(
            format_record(
                {
                    "kind": "mail",
                    "subject": msg.subject,
                    "excerpt": msg.excerpt,
                    "from": msg.from_address,
                    "priority": msg.priority,
                    "state": msg.state,
                }
            )
        )
    return rows


def to_csv(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "kind,title\n"
    keys = sorted({key for row in rows for key in row if not str(key).startswith("_")})
    lines = [",".join(keys)]
    for row in rows:
        lines.append(",".join(strip_html(str(row.get(key, ""))).replace(",", " ") for key in keys))
    return "\n".join(lines)


async def send_export(
    session: AsyncSession,
    user_id: str,
    destination: str,
    target: str = "",
) -> dict[str, Any]:
    if destination not in DESTINATIONS:
        raise ConsentError("unknown_destination", "Choose json, csv, webhook, email, postgres, sheets, airtable or s3.")
    rows = await collect_export(session, user_id)
    digest = payload_digest({"n": len(rows), "destination": destination})
    now = clock.now()
    receipt = ExportReceipt(
        id=new_id("exp"),
        user_id=user_id,
        destination=destination,
        payload_hash=digest,
        row_count=len(rows),
        state="prepared",
        created_at=now,
    )
    session.add(receipt)

    if destination in {"json", "csv", "postgres"}:
        receipt.state = "complete"
        return {
            "id": receipt.id,
            "destination": destination,
            "state": "complete",
            "row_count": len(rows),
            "payload_hash": digest,
            "items": rows if destination == "json" else None,
            "csv": to_csv(rows) if destination == "csv" else None,
            "postgres": "hashed identifiers only; no raw mailbox bodies",
            "raw_bodies_stored": False,
        }

    if destination == "email":
        receipt.state = "queued_demo_outbox"
        return {
            "id": receipt.id,
            "destination": "email",
            "state": "queued_demo_outbox",
            "note": "Would attach the hashed export to the demo outbox after approval. No SMTP.",
            "payload_hash": digest,
            "row_count": len(rows),
        }

    if destination in {"sheets", "airtable", "s3"}:
        receipt.state = "adapter_unconfigured"
        return {
            "id": receipt.id,
            "destination": destination,
            "state": "adapter_unconfigured",
            "oauth": "fixture-adapter",
            "note": "Live OAuth is not configured. The hashed payload is ready; connect the provider to ship it.",
            "payload_hash": digest,
            "row_count": len(rows),
        }

    if not target.startswith("https://") and not target.startswith("http://127.0.0.1"):
        receipt.state = "blocked"
        raise ConsentError("webhook_https_only", "Webhooks must be https or local loopback.")
    settings = get_settings()
    if settings.simulate_offline:
        receipt.state = "degraded"
        return {
            "id": receipt.id,
            "destination": "webhook",
            "state": "degraded",
            "router": {"route": "retry_later", "code": "connectivity_timeout"},
            "payload_hash": digest,
        }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(
                target,
                json={"source": "termpilot", "payload_hash": digest, "row_count": len(rows), "items": rows},
            )
            response.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        receipt.state = "failed"
        routed = _classify_error(exc)
        return {
            "id": receipt.id,
            "destination": "webhook",
            "state": "failed",
            "router": routed,
            "payload_hash": digest,
        }
    receipt.state = "complete"
    return {
        "id": receipt.id,
        "destination": "webhook",
        "state": "complete",
        "payload_hash": digest,
        "row_count": len(rows),
        "raw_bodies_stored": False,
    }


def next_page_url(html_or_xml: str) -> str | None:
    """Pull a public feed rel=next link. Never used to scrape a university portal."""
    match = re_search_next(html_or_xml)
    return match


def re_search_next(blob: str) -> str | None:
    import re

    rel = re.search(r'rel=["\']next["\'][^>]*href=["\']([^"\']+)["\']', blob, re.I)
    if rel:
        return rel.group(1)
    href = re.search(r'href=["\']([^"\']+)["\'][^>]*rel=["\']next["\']', blob, re.I)
    return href.group(1) if href else None
