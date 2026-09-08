"""Student-life newsfeed: public RSS, Reddit, mailbox-gated university notices.

TermPilot signposts like a student representative and a faculty office would:
official links, policy notices, reminders. It does not speak as the dean,
the union, or a counsellor. University items are taken only from the linked
university mailbox — the portal is never scraped.
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from hashlib import sha256
from typing import Any
from xml.etree import ElementTree as ET

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Obligation, SourceObservation
from app.services import clock
from app.settings import get_settings

USER_AGENT = "TermPilot/0.1 (student-life newsfeed; demo)"
_ASAP_WORDS = (
    "visa",
    "deadline",
    "cas",
    "enrol",
    "enroll",
    "funding",
    "strike",
    "overdue",
    "urgent",
    "brp",
    "immigration",
)

RSS_SOURCES: list[dict[str, str]] = [
    {
        "id": "govuk_dfe",
        "channel": "government",
        "label": "GOV.UK Department for Education",
        "url": "https://www.gov.uk/government/organisations/department-for-education.atom",
    },
    {
        "id": "govuk_ukvi",
        "channel": "government",
        "label": "UK Visas and Immigration",
        "url": "https://www.gov.uk/government/organisations/uk-visas-and-immigration.atom",
    },
    {
        "id": "govuk_slc",
        "channel": "government",
        "label": "Student Loans Company",
        "url": "https://www.gov.uk/government/organisations/student-loans-company.atom",
    },
    {
        "id": "bbc_education",
        "channel": "school",
        "label": "BBC Education",
        "url": "https://feeds.bbci.co.uk/news/education/rss.xml",
    },
    {
        "id": "ofs",
        "channel": "school",
        "label": "Office for Students",
        "url": "https://www.officeforstudents.org.uk/feed/",
    },
]

REDDIT_SOURCES: list[dict[str, str]] = [
    {"id": "uniuk", "subreddit": "UniUK", "channel": "community"},
    {"id": "international", "subreddit": "InternationalStudents", "channel": "international"},
    {"id": "ukvisa", "subreddit": "ukvisa", "channel": "international"},
    {"id": "gradadmissions", "subreddit": "gradadmissions", "channel": "career"},
]

DIRECTORY: list[dict[str, str]] = [
    {
        "id": "union_nus",
        "group": "student_union",
        "title": "National Union of Students",
        "url": "https://www.nus.org.uk/",
        "note": "Independent student voice. TermPilot is not your union and does not speak as an officer.",
    },
    {
        "id": "union_advice",
        "group": "student_union",
        "title": "NUS advice and representation",
        "url": "https://www.nus.org.uk/advice",
        "note": "Academic appeals, housing and money. Raise issues through elected reps.",
    },
    {
        "id": "careers_prospects",
        "group": "career",
        "title": "Prospects (graduate careers)",
        "url": "https://www.prospects.ac.uk/",
        "note": "Jobs, placements and further study. TermPilot does not apply on your behalf.",
    },
    {
        "id": "careers_targetjobs",
        "group": "career",
        "title": "targetjobs",
        "url": "https://targetjobs.co.uk/",
        "note": "UK graduate schemes and internships.",
    },
    {
        "id": "wellbeing_nhs",
        "group": "wellbeing",
        "title": "NHS mental health",
        "url": "https://www.nhs.uk/mental-health/",
        "note": "TermPilot is not a counselling service and does not diagnose.",
    },
    {
        "id": "wellbeing_minds",
        "group": "wellbeing",
        "title": "Student Minds",
        "url": "https://www.studentminds.org.uk/",
        "note": "Student mental-health charity. Official support, not this bot.",
    },
    {
        "id": "wellbeing_samaritans",
        "group": "wellbeing",
        "title": "Samaritans",
        "url": "https://www.samaritans.org/",
        "note": "Call 116 123 in the UK, 24/7. TermPilot is not a crisis service.",
    },
    {
        "id": "support_space",
        "group": "student_support",
        "title": "Student Space",
        "url": "https://studentspace.org.uk/",
        "note": "Mental-health support for UK students.",
    },
    {
        "id": "support_finance",
        "group": "student_support",
        "title": "Student Finance England",
        "url": "https://www.gov.uk/student-finance",
        "note": "Tuition and maintenance funding. Official GOV.UK.",
    },
    {
        "id": "support_citizens",
        "group": "student_support",
        "title": "Citizens Advice",
        "url": "https://www.citizensadvice.org.uk/",
        "note": "Housing, money and rights.",
    },
    {
        "id": "intl_ukcisa",
        "group": "international",
        "title": "UKCISA",
        "url": "https://www.ukcisa.org.uk/",
        "note": "Advice body for international students.",
    },
    {
        "id": "intl_visa",
        "group": "international",
        "title": "GOV.UK Student visa",
        "url": "https://www.gov.uk/student-visa",
        "note": "Official Home Office guidance. Do not rely on social posts.",
    },
    {
        "id": "intl_ukvi",
        "group": "international",
        "title": "UK Visas and Immigration",
        "url": "https://www.gov.uk/government/organisations/uk-visas-and-immigration",
        "note": "Policy and operational updates.",
    },
    {
        "id": "intl_bc",
        "group": "international",
        "title": "British Council Study UK",
        "url": "https://study-uk.britishcouncil.org/",
        "note": "Study-in-the-UK guidance.",
    },
    {
        "id": "community_meetup",
        "group": "community",
        "title": "Meetup student groups",
        "url": "https://www.meetup.com/topics/students/",
        "note": "Public community directory only.",
    },
    {
        "id": "community_nus",
        "group": "community",
        "title": "NUS campaigns and events",
        "url": "https://www.nus.org.uk/",
        "note": "Student community and campaigns.",
    },
]

ROLE_NOTE = (
    "TermPilot signposts the way a student representative and a faculty office would: "
    "official links, policy notices and reminders. It does not speak as the dean, "
    "the union, or a counsellor, and it will not impersonate staff."
)
CRISIS_NOTE = (
    "TermPilot is not a crisis service. If you are in danger, contact emergency services "
    "or Samaritans on 116 123 (UK)."
)
UNIVERSITY_LOCK = (
    "Connect the linked university mailbox (Forwarded student mail) to surface notices "
    "that arrived at your university address. TermPilot does not scrape the university portal."
)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return (node.text or "").strip()


def _strip_html(value: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", cleaned).strip()


def _parse_when(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
        return parsed


def _priority(title: str, flagged: str | None = None) -> str:
    if flagged in {"asap", "high"}:
        return "asap"
    blob = title.lower()
    if any(word in blob for word in _ASAP_WORDS):
        return "asap"
    return "normal"


def _item_id(url: str, title: str) -> str:
    digest = sha256(f"{url}|{title}".encode()).hexdigest()[:12]
    return f"feed_{digest}"


def parse_feed_xml(
    payload: str, *, channel: str, source_label: str, source_url: str
) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError:
        return []
    items: list[dict[str, Any]] = []
    kind = _local(root.tag).lower()
    if kind == "feed":
        entries = [child for child in root if _local(child.tag) == "entry"]
    elif kind == "rss":
        entries = [
            child
            for channel_el in root
            if _local(channel_el.tag) == "channel"
            for child in channel_el
            if _local(child.tag) == "item"
        ]
    else:
        entries = [child for child in root.iter() if _local(child.tag) in {"item", "entry"}]
    for entry in entries[:8]:
        kids = {_local(child.tag): child for child in entry}
        title = _strip_html(_text(kids.get("title")) or "Untitled")
        summary = _strip_html(
            _text(kids.get("summary") or kids.get("description") or kids.get("content"))
        )
        link = ""
        link_el = kids.get("link")
        if link_el is not None:
            link = (link_el.get("href") or _text(link_el)).strip()
        if not link:
            for child in entry:
                if _local(child.tag) == "link" and (child.get("rel") in {None, "alternate"}):
                    link = (child.get("href") or _text(child)).strip()
                    if link:
                        break
        published = _parse_when(
            _text(
                kids.get("published")
                or kids.get("updated")
                or kids.get("pubDate")
                or kids.get("date")
            )
        )
        items.append(
            {
                "id": _item_id(link or source_url, title),
                "title": title[:240],
                "summary": summary[:400],
                "url": link or source_url,
                "published": published.isoformat() if published else None,
                "channel": channel,
                "source_label": source_label,
                "source_kind": "rss",
                "source_feed": source_url,
                "stale": False,
                "priority": _priority(title),
                "university_gated": False,
            }
        )
    return items


async def _fetch_text(client: httpx.AsyncClient, url: str) -> str | None:
    try:
        response = await client.get(url)
        response.raise_for_status()
        return response.text
    except Exception:
        return None


async def _pull_rss(
    client: httpx.AsyncClient, spec: dict[str, str]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    body = await _fetch_text(client, spec["url"])
    if not body:
        return [], {"id": spec["id"], "ok": False, "url": spec["url"], "kind": "rss"}
    items = parse_feed_xml(
        body,
        channel=spec["channel"],
        source_label=spec["label"],
        source_url=spec["url"],
    )
    return items, {
        "id": spec["id"],
        "ok": bool(items),
        "url": spec["url"],
        "kind": "rss",
        "count": len(items),
    }


async def _pull_reddit(
    client: httpx.AsyncClient, spec: dict[str, str]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    sub = spec["subreddit"]
    # Public Atom works; Reddit JSON currently returns 403 without OAuth.
    url = f"https://www.reddit.com/r/{sub}/.rss"
    body = await _fetch_text(client, url)
    items: list[dict[str, Any]] = []
    if body and "<html" not in body[:80].lower():
        items = parse_feed_xml(
            body,
            channel=spec["channel"],
            source_label=f"Reddit r/{sub}",
            source_url=url,
        )
        for item in items:
            item["source_kind"] = "reddit"
    if items:
        return items, {
            "id": spec["id"],
            "ok": True,
            "url": url,
            "kind": "reddit",
            "count": len(items),
        }
    # Honest degrade: link the real subreddit, do not invent posts.
    hub = {
        "id": f"reddit_hub_{sub.lower()}",
        "title": f"r/{sub} community",
        "summary": "Live Reddit Atom was unavailable (block or rate limit). This is the public subreddit, not a fabricated post.",
        "url": f"https://www.reddit.com/r/{sub}/",
        "published": None,
        "channel": spec["channel"],
        "source_label": f"Reddit r/{sub}",
        "source_kind": "reddit",
        "source_feed": url,
        "stale": True,
        "priority": "normal",
        "university_gated": False,
    }
    return [hub], {
        "id": spec["id"],
        "ok": False,
        "url": url,
        "kind": "reddit",
        "count": 0,
        "stale": True,
    }


def _fallback_public() -> list[dict[str, Any]]:
    path = get_settings().fixtures_root / "feeds" / "public_fallback.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = []
    for raw in payload.get("items", []):
        items.append(
            {
                "id": raw["id"],
                "title": raw["title"],
                "summary": raw.get("summary", ""),
                "url": raw.get("url"),
                "published": raw.get("published"),
                "channel": raw.get("channel", "community"),
                "source_label": raw.get("source_label", "offline_fixture"),
                "source_kind": "fixture",
                "source_feed": "fixtures/feeds/public_fallback.json",
                "stale": True,
                "priority": raw.get("priority", "normal"),
                "university_gated": False,
            }
        )
    return items


def _university_mailbox_fixture() -> list[dict[str, Any]]:
    path = get_settings().fixtures_root / "feeds" / "university_mailbox.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = []
    for raw in payload.get("items", []):
        items.append(
            {
                "id": raw["id"],
                "title": raw["title"],
                "summary": raw.get("summary", ""),
                "url": raw.get("url"),
                "published": raw.get("published"),
                "channel": "university",
                "source_label": f"University mailbox · {raw.get('from', 'unknown')}",
                "source_kind": "university_mailbox",
                "source_feed": "fixtures/feeds/university_mailbox.json",
                "stale": False,
                "priority": raw.get("priority") or _priority(raw["title"]),
                "university_gated": True,
                "from": raw.get("from"),
                "tags": raw.get("tags") or [],
                "reminder": bool(raw.get("reminder")),
            }
        )
    return items


def _observation_to_item(row: SourceObservation) -> dict[str, Any] | None:
    payload = row.payload_json if isinstance(row.payload_json, dict) else {}
    sender = str(payload.get("from") or "")
    if not sender.endswith("@northbridge.example") and "northbridge" not in sender.lower():
        return None
    title = str(payload.get("subject") or row.excerpt or "University mailbox notice")
    body = str(payload.get("body") or row.excerpt or "")
    return {
        "id": f"mail_{row.id}",
        "title": title[:240],
        "summary": _strip_html(body)[:400],
        "url": None,
        "published": row.observed_at.isoformat(),
        "channel": "university",
        "source_label": f"University mailbox · {sender or row.source_type}",
        "source_kind": "university_mailbox",
        "source_feed": row.source_reference,
        "stale": False,
        "priority": _priority(title),
        "university_gated": True,
        "from": sender,
        "reminder": True,
    }


async def _university_authorised(session: AsyncSession, user_id: str) -> bool:
    from app.services.identity import get_connection

    row = await get_connection(session, user_id, "src_email")
    return bool(row and row.user_id == user_id and row.permission_state == "granted")


async def _university_items(session: AsyncSession, user_id: str) -> list[dict[str, Any]]:
    items = _university_mailbox_fixture()
    observations = (
        (
            await session.execute(
                select(SourceObservation).where(
                    SourceObservation.user_id == user_id,
                    SourceObservation.source_type.in_(("email", "mailbox")),
                )
            )
        )
        .scalars()
        .all()
    )
    seen = {item["title"] for item in items}
    for row in observations:
        converted = _observation_to_item(row)
        if converted is None or converted["title"] in seen:
            continue
        items.append(converted)
        seen.add(converted["title"])
    return items


async def _reminders(
    session: AsyncSession, user_id: str, feed_items: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    now = clock.now()
    horizon = now + timedelta(days=14)
    out: list[dict[str, Any]] = []
    obligations = (
        (await session.execute(select(Obligation).where(Obligation.user_id == user_id)))
        .scalars()
        .all()
    )
    for row in obligations:
        if row.status in {"complete", "cancelled"} or row.due_at is None:
            continue
        if row.due_at > horizon:
            continue
        hours = (row.due_at - now).total_seconds() / 3600
        out.append(
            {
                "id": f"rem_{row.id}",
                "kind": "obligation",
                "title": row.title,
                "due_at": row.due_at.isoformat(),
                "priority": "asap" if hours <= 72 else row.priority,
                "source_label": f"{row.source_type} · {row.course_or_context}",
                "channel": "reminders",
            }
        )
    for item in feed_items:
        if item.get("reminder") or item.get("priority") == "asap":
            out.append(
                {
                    "id": f"rem_{item['id']}",
                    "kind": "notice",
                    "title": item["title"],
                    "due_at": item.get("published"),
                    "priority": item.get("priority", "normal"),
                    "source_label": item.get("source_label", ""),
                    "channel": item.get("channel", "university"),
                    "url": item.get("url"),
                }
            )
    out.sort(key=lambda row: (0 if row["priority"] == "asap" else 1, row.get("due_at") or ""))
    return out[:20]


async def assemble_feeds(
    session: AsyncSession,
    user_id: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    sources_status: list[dict[str, Any]] = []
    live_items: list[dict[str, Any]] = []
    offline = settings.simulate_offline

    if not offline:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml, application/atom+xml, application/json, text/xml",
        }
        own_client = client is None
        http = client or httpx.AsyncClient(timeout=8.0, headers=headers, follow_redirects=True)
        try:
            rss_results = await asyncio.gather(*[_pull_rss(http, spec) for spec in RSS_SOURCES])
            for items, status in rss_results:
                sources_status.append(status)
                live_items.extend(items)
            # Reddit rate-limits parallel JSON/RSS; pull one subreddit at a time.
            for spec in REDDIT_SOURCES:
                items, status = await _pull_reddit(http, spec)
                sources_status.append(status)
                live_items.extend(items)
        finally:
            if own_client:
                await http.aclose()

    stale = False
    if not live_items:
        live_items = _fallback_public()
        stale = True
        sources_status.append(
            {"id": "offline_fixture", "ok": True, "kind": "fixture", "stale": True}
        )

    university_ok = await _university_authorised(session, user_id)
    university_items: list[dict[str, Any]] = []
    if university_ok:
        university_items = await _university_items(session, user_id)
        live_items.extend(university_items)

    deduped: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for item in live_items:
        key = item.get("id") or item["title"]
        if key in seen_ids:
            continue
        seen_ids.add(key)
        deduped.append(item)

    def _sort_key(item: dict[str, Any]) -> tuple[int, float]:
        raw = item.get("published")
        parsed = _parse_when(raw if isinstance(raw, str) else None)
        stamp = parsed.timestamp() if parsed else 0.0
        return (0 if item.get("priority") == "asap" else 1, -stamp)

    deduped.sort(key=_sort_key)
    reminders = await _reminders(
        session, user_id, university_items or [i for i in deduped if i.get("reminder")]
    )
    live_count = sum(1 for row in sources_status if row.get("ok") and not row.get("stale"))
    return {
        "now": clock.now().isoformat(),
        "role_note": ROLE_NOTE,
        "crisis_note": CRISIS_NOTE,
        "university_authorised": university_ok,
        "university_lock": None if university_ok else UNIVERSITY_LOCK,
        "university_gate": "src_email",
        "stale": stale,
        "pulled": {
            "live_sources": live_count,
            "sources": sources_status,
        },
        "items": deduped[:48],
        "reminders": reminders,
        "directory": DIRECTORY,
        "channels": [
            "university",
            "government",
            "school",
            "international",
            "community",
            "career",
            "wellbeing",
        ],
    }
