"""Student productivity workspace: connectors, drafts, notes, workflows.

One-click connect always works. Live OAuth starts when provider client IDs
are set in the environment; otherwise the same click uses a labelled fixture
adapter. Outbound mail never leaves the demo outbox without Guardian + approval.
"""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlencode

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import (
    AgentName,
    AgentRunState,
    ApprovalState,
    ConsentPurpose,
)
from app.domain.ids import new_id
from app.domain.models import (
    ApprovalRequest,
    CalendarEvent,
    ConflictingClaim,
    ConsentGrant,
    Obligation,
    OutboundMessage,
    SourceConnection,
    SourceObservation,
    WorkflowRun,
    WorkspaceNote,
)
from app.policies.consent import ConsentError, require_consent
from app.services import clock
from app.services.audit import record_audit, run_agent
from app.services.identity import catalog_id_of, connection_id_for, get_connection, scoped_id
from app.settings import get_settings

CONNECTOR_CATALOG: list[dict[str, Any]] = [
    {
        "id": "src_lms",
        "source_type": "lms",
        "label": "Northbridge LMS",
        "kind": "academic",
        "capability": "Read assignments. Official course record.",
    },
    {
        "id": "src_email",
        "source_type": "email",
        "label": "University email",
        "kind": "academic",
        "capability": "Read your university mailbox (Google or Microsoft 365). Writes still need on-screen approval.",
    },
    {
        "id": "src_cal",
        "source_type": "calendar",
        "label": "Demo calendar",
        "kind": "academic",
        "capability": "Read fixed events. Writes require approval.",
    },
    {
        "id": "src_upload",
        "source_type": "upload",
        "label": "Local uploads",
        "kind": "academic",
        "capability": "Read uploaded notes.",
    },
    {
        "id": "src_mailbox",
        "source_type": "mailbox",
        "label": "Student inbox",
        "kind": "productivity",
        "capability": "Gmail or Outlook inbox. Drafts stay in the outbox until you approve.",
    },
    {
        "id": "src_linkedin",
        "source_type": "linkedin",
        "label": "LinkedIn",
        "kind": "social",
        "capability": "Read recruiting opportunities. No profile posts.",
    },
    {
        "id": "src_orcid",
        "source_type": "orcid",
        "label": "ORCID",
        "kind": "social",
        "capability": "Read public works. No identity inference.",
    },
    {
        "id": "src_x",
        "source_type": "x",
        "label": "X",
        "kind": "social",
        "capability": "Read a selected timeline. No autonomous posting.",
    },
    {
        "id": "src_notion",
        "source_type": "notion",
        "label": "Notion",
        "kind": "productivity",
        "capability": "Organise notes. Does not write assessed homework.",
    },
    {
        "id": "src_slack",
        "source_type": "slack",
        "label": "Slack",
        "kind": "productivity",
        "capability": "Draft collaboration messages. Not sent until approved.",
    },
    {
        "id": "src_github",
        "source_type": "github",
        "label": "GitHub",
        "kind": "productivity",
        "capability": "Read issues and repos you already own. Does not push code or complete labs.",
    },
    {
        "id": "src_jira",
        "source_type": "jira",
        "label": "Jira",
        "kind": "productivity",
        "capability": "Read project tickets. Does not close assessed work.",
    },
    {
        "id": "src_discord",
        "source_type": "discord",
        "label": "Discord",
        "kind": "productivity",
        "capability": "Read society channels. Drafts stay unsent until you approve.",
    },
    {
        "id": "src_teams",
        "source_type": "teams",
        "label": "Microsoft Teams",
        "kind": "productivity",
        "capability": "Read class team channels. Nothing is posted without approval.",
    },
    {
        "id": "src_gdrive",
        "source_type": "gdrive",
        "label": "Google Drive",
        "kind": "productivity",
        "capability": "Read files you already own. Does not write assessed homework.",
    },
]

# Real provider entry points. Authorize URLs are assembled only when a client id is set.
PRODUCTION: dict[str, dict[str, Any]] = {
    "src_lms": {
        "docs_url": "https://canvas.instructure.com/doc/api/file.oauth.html",
        "authorize_base": "https://canvas.instructure.com/login/oauth2/auth",
        "scopes": "",
        "env": ["CANVAS_CLIENT_ID", "CANVAS_CLIENT_SECRET"],
        "client_attr": "canvas_client_id",
    },
    "src_email": {
        "docs_url": "https://developers.google.com/gmail/api/auth/about-auth",
        "authorize_base": "https://accounts.google.com/o/oauth2/v2/auth",
        "scopes": "https://www.googleapis.com/auth/gmail.readonly",
        "env": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "MICROSOFT_CLIENT_ID"],
        "client_attr": "google_client_id",
        "alt_attr": "microsoft_client_id",
        "alt_authorize_base": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "alt_scopes": "Mail.Read offline_access",
        "alt_docs_url": "https://learn.microsoft.com/en-us/graph/auth-v2-user",
    },
    "src_cal": {
        "docs_url": "https://developers.google.com/calendar/api/guides/auth",
        "authorize_base": "https://accounts.google.com/o/oauth2/v2/auth",
        "scopes": "https://www.googleapis.com/auth/calendar.readonly",
        "env": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
        "client_attr": "google_client_id",
    },
    "src_upload": {
        "docs_url": "https://developer.mozilla.org/en-US/docs/Web/API/File_API",
        "authorize_base": None,
        "scopes": "",
        "env": [],
        "client_attr": None,
    },
    "src_mailbox": {
        "docs_url": "https://learn.microsoft.com/en-us/graph/auth-v2-user",
        "authorize_base": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "scopes": "Mail.Read Mail.ReadWrite offline_access",
        "env": ["MICROSOFT_CLIENT_ID", "MICROSOFT_CLIENT_SECRET", "GOOGLE_CLIENT_ID"],
        "client_attr": "microsoft_client_id",
        "alt_docs_url": "https://developers.google.com/gmail/api/auth/about-auth",
    },
    "src_linkedin": {
        "docs_url": "https://learn.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow",
        "authorize_base": "https://www.linkedin.com/oauth/v2/authorization",
        "scopes": "profile email",
        "env": ["LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET"],
        "client_attr": "linkedin_client_id",
    },
    "src_orcid": {
        "docs_url": "https://info.orcid.org/documentation/api-tutorials/api-tutorial-get-and-authenticated-orcid-id/",
        "authorize_base": "https://orcid.org/oauth/authorize",
        "scopes": "/authenticate",
        "env": ["ORCID_CLIENT_ID", "ORCID_CLIENT_SECRET"],
        "client_attr": "orcid_client_id",
    },
    "src_x": {
        "docs_url": "https://docs.x.com/fundamentals/authentication/oauth-2-0/authorization-code",
        "authorize_base": "https://twitter.com/i/oauth2/authorize",
        "scopes": "tweet.read users.read offline.access",
        "env": ["X_CLIENT_ID", "X_CLIENT_SECRET"],
        "client_attr": "x_client_id",
    },
    "src_notion": {
        "docs_url": "https://developers.notion.com/docs/authorization",
        "authorize_base": "https://api.notion.com/v1/oauth/authorize",
        "scopes": "",
        "env": ["NOTION_CLIENT_ID", "NOTION_CLIENT_SECRET"],
        "client_attr": "notion_client_id",
    },
    "src_slack": {
        "docs_url": "https://api.slack.com/authentication/oauth-v2",
        "authorize_base": "https://slack.com/oauth/v2/authorize",
        "scopes": "channels:history chat:write",
        "env": ["SLACK_CLIENT_ID", "SLACK_CLIENT_SECRET"],
        "client_attr": "slack_client_id",
    },
    "src_github": {
        "docs_url": "https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps",
        "authorize_base": "https://github.com/login/oauth/authorize",
        "scopes": "read:user repo",
        "env": ["GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET"],
        "client_attr": "github_client_id",
    },
    "src_jira": {
        "docs_url": "https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/",
        "authorize_base": "https://auth.atlassian.com/authorize",
        "scopes": "read:jira-work offline_access",
        "env": ["JIRA_CLIENT_ID", "JIRA_CLIENT_SECRET"],
        "client_attr": "jira_client_id",
        "extra_params": {"audience": "api.atlassian.com", "prompt": "consent"},
    },
    "src_discord": {
        "docs_url": "https://discord.com/developers/docs/topics/oauth2",
        "authorize_base": "https://discord.com/api/oauth2/authorize",
        "scopes": "identify guilds",
        "env": ["DISCORD_CLIENT_ID", "DISCORD_CLIENT_SECRET"],
        "client_attr": "discord_client_id",
    },
    "src_teams": {
        "docs_url": "https://learn.microsoft.com/en-us/graph/auth-v2-user",
        "authorize_base": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "scopes": "Team.ReadBasic.All ChannelMessage.Read.All offline_access",
        "env": ["MICROSOFT_CLIENT_ID", "MICROSOFT_CLIENT_SECRET"],
        "client_attr": "microsoft_client_id",
    },
    "src_gdrive": {
        "docs_url": "https://developers.google.com/drive/api/guides/about-auth",
        "authorize_base": "https://accounts.google.com/o/oauth2/v2/auth",
        "scopes": "https://www.googleapis.com/auth/drive.readonly",
        "env": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
        "client_attr": "google_client_id",
    },
}


def production_status(spec: dict[str, Any]) -> dict[str, Any]:
    extra = PRODUCTION.get(spec["id"], {})
    settings = get_settings()
    attr = extra.get("client_attr")
    client = getattr(settings, attr, None) if attr else None
    base = extra.get("authorize_base")
    scopes = extra.get("scopes") or ""
    docs = extra.get("docs_url")
    if not client and extra.get("alt_attr"):
        alt = getattr(settings, str(extra["alt_attr"]), None)
        if alt:
            client = alt
            base = extra.get("alt_authorize_base") or base
            scopes = extra.get("alt_scopes") or scopes
            docs = extra.get("alt_docs_url") or docs
    ready = bool(client)
    authorize = None
    if ready and base:
        params = {
            "client_id": client,
            "response_type": "code",
            "redirect_uri": f"{settings.frontend_origin}/connectors/oauth/callback",
            "state": spec["id"],
        }
        if scopes:
            params["scope"] = str(scopes)
        extra_params = extra.get("extra_params") or {}
        if isinstance(extra_params, dict):
            params.update({str(k): str(v) for k, v in extra_params.items()})
        authorize = f"{base}?{urlencode(params)}"
    return {
        "one_click": True,
        "auto_reconnect": True,
        "oauth_ready": ready,
        "docs_url": docs,
        "authorize_url": authorize,
        "production_url": authorize or docs,
        "env": list(extra.get("env") or []),
        "scopes": scopes,
        "setup": None
        if ready
        else (
            "One-click Connect uses the fixture adapter until "
            + ", ".join(extra.get("env") or ["provider client id"])
            + " is set. The production link stays available."
        ),
    }


WORKFLOWS: list[dict[str, Any]] = [
    {
        "name": "clarify-deadline",
        "title": "Draft deadline clarification",
        "graph": ["guardian", "scout", "workflow"],
        "description": "Turn the open deadline conflict into an unsent clarification email.",
    },
    {
        "name": "organise-notes",
        "title": "Organise Notion inbox",
        "graph": ["guardian", "workflow"],
        "description": "Tag and file synthetic Notion notes. Never completes assessed work.",
    },
    {
        "name": "slack-standup",
        "title": "Draft lab standup",
        "graph": ["guardian", "workflow"],
        "description": "Draft a Slack standup from today's plan. Approval required to send.",
    },
    {
        "name": "recruiting-brief",
        "title": "Recruiting brief",
        "graph": ["guardian", "scout", "workflow"],
        "description": "Summarise LinkedIn + internship obligation into a brief.",
    },
]


def _fixture(relative: str) -> dict[str, Any]:
    path = get_settings().fixtures_root / relative
    return cast(dict[str, Any], json.loads(Path(path).read_text(encoding="utf-8")))


async def seed_optional_connectors(session: AsyncSession, user_id: str) -> None:
    now = clock.now()
    existing = {
        catalog_id_of(row.id, user_id)
        for row in (
            await session.execute(
                select(SourceConnection).where(SourceConnection.user_id == user_id)
            )
        )
        .scalars()
        .all()
    }
    for item in CONNECTOR_CATALOG:
        if item["id"] in existing:
            continue
        granted = item["kind"] == "academic"
        session.add(
            SourceConnection(
                id=connection_id_for(user_id, item["id"]),
                user_id=user_id,
                source_type=item["source_type"],
                label=item["label"],
                health="healthy" if granted else "unavailable",
                permission_state="granted" if granted else "missing",
                last_success_at=now if granted else None,
                stale_after_minutes=180,
                created_at=now,
            )
        )


async def list_connectors(session: AsyncSession, user_id: str) -> list[dict[str, Any]]:
    rows = (
        (await session.execute(select(SourceConnection).where(SourceConnection.user_id == user_id)))
        .scalars()
        .all()
    )
    by_id = {catalog_id_of(row.id, user_id): row for row in rows}
    out: list[dict[str, Any]] = []
    for item in CONNECTOR_CATALOG:
        row = by_id.get(item["id"])
        prod = production_status(item)
        out.append(
            {
                "id": item["id"],
                "source_type": item["source_type"],
                "label": item["label"],
                "kind": item["kind"],
                "capability": item["capability"],
                "health": row.health if row else "unavailable",
                "permission_state": row.permission_state if row else "missing",
                "last_success_at": row.last_success_at.isoformat()
                if row and row.last_success_at
                else None,
                "connected": bool(row and row.permission_state == "granted"),
                "oauth": "oauth-ready" if prod["oauth_ready"] else "fixture-adapter",
                **prod,
            }
        )
    return out


async def connect_connector(
    session: AsyncSession, user_id: str, connector_id: str
) -> dict[str, Any]:
    spec = next((c for c in CONNECTOR_CATALOG if c["id"] == connector_id), None)
    if spec is None:
        raise LookupError("unknown_connector")
    now = clock.now()
    row = await get_connection(session, user_id, connector_id)
    if row is None or row.user_id != user_id:
        raise LookupError("unknown_connector")
    session.add(
        ConsentGrant(
            id=new_id("cns"),
            user_id=user_id,
            purpose=ConsentPurpose.SOURCE_READ.value,
            source_type=spec["source_type"],
            granted=True,
            granted_at=now,
            expires_at=now + timedelta(days=30),
            scope_note=spec["capability"],
        )
    )
    if spec["source_type"] == "mailbox":
        session.add(
            ConsentGrant(
                id=new_id("cns"),
                user_id=user_id,
                purpose=ConsentPurpose.MESSAGE_SEND.value,
                source_type="mailbox",
                granted=True,
                granted_at=now,
                expires_at=now + timedelta(days=30),
                scope_note="Demo outbox only. No SMTP.",
            )
        )
    if spec["source_type"] == "notion":
        session.add(
            ConsentGrant(
                id=new_id("cns"),
                user_id=user_id,
                purpose=ConsentPurpose.NOTES_WRITE.value,
                source_type="notion",
                granted=True,
                granted_at=now,
                expires_at=now + timedelta(days=30),
                scope_note="Organise synthetic Notion notes.",
            )
        )
    if spec["source_type"] == "slack":
        session.add(
            ConsentGrant(
                id=new_id("cns"),
                user_id=user_id,
                purpose=ConsentPurpose.MESSAGE_SEND.value,
                source_type="slack",
                granted=True,
                granted_at=now,
                expires_at=now + timedelta(days=30),
                scope_note="Demo Slack drafts only.",
            )
        )
    row.permission_state = "granted"
    row.health = "healthy"
    row.last_success_at = now
    row.last_error_code = None
    row.last_error_message = None
    await _ingest_fixture(session, user_id, spec)
    await record_audit(
        session,
        user_id=user_id,
        correlation_id=connector_id,
        agent=AgentName.GUARDIAN.value,
        event_type="connector_connected",
        object_type="source",
        object_id=connector_id,
        summary=f"Connected {spec['label']} via fixture adapter.",
        policy_check="consent_granted",
    )
    prod = production_status(spec)
    adapter = "oauth" if prod["oauth_ready"] and prod.get("authorize_url") else "fixture"
    return {
        "id": connector_id,
        "connected": True,
        "adapter": adapter,
        "one_click": True,
        "oauth_ready": prod["oauth_ready"],
        "authorize_url": prod.get("authorize_url"),
        "production_url": prod["production_url"],
        "last_success_at": now.isoformat(),
        "auto_reconnect": True,
        "policy": "consent_granted",
    }


async def connect_all(
    session: AsyncSession, user_id: str, connector_ids: list[str] | None = None
) -> dict[str, Any]:
    await seed_optional_connectors(session, user_id)
    await session.flush()
    wanted = connector_ids or [item["id"] for item in CONNECTOR_CATALOG]
    connected: list[dict[str, Any]] = []
    for connector_id in wanted:
        spec = next((c for c in CONNECTOR_CATALOG if c["id"] == connector_id), None)
        if spec is None:
            continue
        row = await get_connection(session, user_id, connector_id)
        if row is not None and row.user_id == user_id and row.permission_state == "granted":
            connected.append({"id": connector_id, "connected": True, "already": True})
            continue
        connected.append(await connect_connector(session, user_id, connector_id))
    return {
        "one_click": True,
        "connected": connected,
        "count": sum(1 for row in connected if row.get("connected")),
    }


def oauth_start(connector_id: str) -> dict[str, Any]:
    spec = next((c for c in CONNECTOR_CATALOG if c["id"] == connector_id), None)
    if spec is None:
        raise LookupError("unknown_connector")
    prod = production_status(spec)
    return {
        "id": connector_id,
        "label": spec["label"],
        "one_click": True,
        **prod,
    }


async def disconnect_connector(
    session: AsyncSession, user_id: str, connector_id: str
) -> dict[str, Any]:
    row = await get_connection(session, user_id, connector_id)
    if row is None or row.user_id != user_id:
        raise LookupError("unknown_connector")
    row.permission_state = "revoked"
    row.health = "permission_revoked"
    grants = (
        (
            await session.execute(
                select(ConsentGrant).where(
                    ConsentGrant.user_id == user_id,
                    ConsentGrant.source_type == row.source_type,
                    ConsentGrant.revoked_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    now = clock.now()
    for grant in grants:
        if (
            grant.purpose == ConsentPurpose.SOURCE_READ.value
            or grant.source_type == row.source_type
        ):
            grant.granted = False
            grant.revoked_at = now
    await record_audit(
        session,
        user_id=user_id,
        correlation_id=connector_id,
        agent=AgentName.GUARDIAN.value,
        event_type="connector_disconnected",
        object_type="source",
        object_id=connector_id,
        summary=f"Disconnected {row.label}.",
        policy_check="consent_revoked",
    )
    return {"id": connector_id, "connected": False}


async def _ingest_fixture(session: AsyncSession, user_id: str, spec: dict[str, Any]) -> None:
    now = clock.now()
    payload: dict[str, Any]
    relative = {
        "linkedin": "linkedin/profile.json",
        "orcid": "orcid/works.json",
        "x": "x/timeline.json",
        "notion": "notion/notes.json",
        "slack": "slack/channels.json",
        "mailbox": "email/lab_report_reminder.json",
        "github": "github/issues.json",
        "jira": "jira/issues.json",
        "discord": "discord/channels.json",
        "teams": "teams/channels.json",
        "gdrive": "gdrive/files.json",
    }.get(spec["source_type"])
    if relative is None:
        return
    payload = _fixture(relative)
    connection_id = connection_id_for(user_id, spec["id"])
    if spec["source_type"] == "notion":
        for page in payload.get("pages", []):
            note_id = scoped_id(user_id, str(page["id"]))
            exists = await session.get(WorkspaceNote, note_id)
            if exists is None:
                session.add(
                    WorkspaceNote(
                        id=note_id,
                        user_id=user_id,
                        source="notion",
                        title=page["title"],
                        body=page["body"],
                        tags_json=list(page.get("tags") or []),
                        organised=False,
                        created_at=now,
                    )
                )
    session.add(
        SourceObservation(
            id=new_id("obs"),
            user_id=user_id,
            connection_id=connection_id,
            source_type=spec["source_type"],
            source_reference=f"fixtures/{relative}",
            source_authority="tertiary",
            observed_at=now,
            content_digest=new_id("dig"),
            excerpt=spec["label"] + " snapshot imported.",
            payload_json=payload,
            injection_flagged=False,
        )
    )


async def meetings(session: AsyncSession, user_id: str) -> list[dict[str, Any]]:
    seeded = _fixture("meetings/upcoming.json").get("meetings", [])
    events = (
        (
            await session.execute(
                select(CalendarEvent).where(
                    CalendarEvent.user_id == user_id, CalendarEvent.rolled_back.is_(False)
                )
            )
        )
        .scalars()
        .all()
    )
    items = list(seeded)
    for event in events:
        items.append(
            {
                "id": event.id,
                "title": event.title,
                "start_at": event.start_at.isoformat(),
                "end_at": event.end_at.isoformat(),
                "join_url": None,
                "provider": event.source,
            }
        )
    items.sort(key=lambda row: str(row.get("start_at")))
    return items


async def calendar_week(session: AsyncSession, user_id: str) -> dict[str, Any]:
    start = clock.now().replace(hour=0, minute=0, second=0, microsecond=0)
    days = []
    meet = await meetings(session, user_id)
    for offset in range(7):
        day = start + timedelta(days=offset)
        key = day.date().isoformat()
        days.append(
            {
                "date": key,
                "label": day.strftime("%a %d %b"),
                "meetings": [m for m in meet if str(m.get("start_at", "")).startswith(key)],
            }
        )
    return {"horizon_start": start.isoformat(), "days": days, "live": True}


async def draft_email(
    session: AsyncSession,
    user_id: str,
    to_address: str,
    subject: str,
    body: str,
    channel: str = "email",
) -> dict[str, Any]:
    connector_id = "src_slack" if channel == "slack" else "src_mailbox"
    connector = await get_connection(session, user_id, connector_id)
    if connector is None or connector.permission_state != "granted":
        raise ConsentError(
            "connector_disconnected",
            "Connect Slack first." if channel == "slack" else "Connect the student mailbox first.",
        )
    now = clock.now()
    message = OutboundMessage(
        id=new_id("msg"),
        user_id=user_id,
        channel=channel,
        to_address=to_address,
        subject=subject,
        body=body,
        state="draft",
        created_at=now,
    )
    session.add(message)
    await session.flush()
    approval = ApprovalRequest(
        id=new_id("apr"),
        user_id=user_id,
        action_type="message_send",
        target_system=f"demo_{channel}",
        reason=f"Send drafted {channel} message.",
        diff_json={
            "create": [],
            "message": {
                "id": message.id,
                "to": to_address,
                "subject": subject,
                "body": body[:800],
            },
        },
        state=ApprovalState.PENDING.value,
        idempotency_key=f"msg-{message.id}",
        reversible=True,
        expires_at=now + timedelta(minutes=get_settings().approval_ttl_minutes),
        created_at=now,
    )
    session.add(approval)
    await session.flush()
    message.approval_id = approval.id
    await record_audit(
        session,
        user_id=user_id,
        correlation_id=message.id,
        agent=AgentName.GUARDIAN.value,
        event_type="message_drafted",
        object_type="message",
        object_id=message.id,
        approval_state=approval.state,
        summary="Message drafted. Not sent.",
        policy_check="human_in_the_loop",
    )
    return {
        "message_id": message.id,
        "approval_id": approval.id,
        "state": "draft",
        "sent": False,
    }


async def send_approved_message(
    session: AsyncSession, user_id: str, message_id: str
) -> dict[str, Any]:
    message = await session.get(OutboundMessage, message_id)
    if message is None or message.user_id != user_id:
        raise LookupError("message_not_found")
    if message.state == "sent":
        return {"status": "idempotent", "message_id": message.id, "sent": True}
    if not message.approval_id:
        raise ConsentError("approval_missing", "No approval is attached to this draft.")
    approval = await session.get(ApprovalRequest, message.approval_id)
    if approval is None or approval.state not in {
        ApprovalState.APPROVED.value,
        ApprovalState.APPLIED.value,
    }:
        raise ConsentError("approval_not_granted", "Approve the draft before send.")
    await require_consent(session, user_id, ConsentPurpose.MESSAGE_SEND)
    message.state = "sent"
    message.sent_at = clock.now()
    approval.state = ApprovalState.APPLIED.value
    approval.applied_at = clock.now()
    await record_audit(
        session,
        user_id=user_id,
        correlation_id=message.id,
        agent=AgentName.GUARDIAN.value,
        event_type="message_sent_demo_outbox",
        object_type="message",
        object_id=message.id,
        approval_state=approval.state,
        summary="Copied to the demo outbox. No external SMTP.",
    )
    return {"status": "sent_demo_outbox", "message_id": message.id, "sent": True}


async def organise_notes(session: AsyncSession, user_id: str) -> dict[str, Any]:
    await require_consent(session, user_id, ConsentPurpose.NOTES_WRITE, "notion")
    notes = (
        (await session.execute(select(WorkspaceNote).where(WorkspaceNote.user_id == user_id)))
        .scalars()
        .all()
    )
    if not notes:
        raise ConsentError("notion_empty", "Connect Notion first so notes can be imported.")

    async def work(_run: Any) -> tuple[AgentRunState, str, str | None]:
        for note in notes:
            tags = list(note.tags_json or [])
            if "inbox" in tags:
                tags = [t for t in tags if t != "inbox"] + ["filed"]
            if "personal" in tags:
                note.organised = True
            elif any(
                token in note.title.lower() + note.body.lower() for token in ("essay", "exam")
            ):
                tags = sorted(set(tags + ["academic-ref-only"]))
                note.organised = True
            else:
                note.organised = True
            note.tags_json = tags
        return AgentRunState.PASSED, f"notes={len(notes)}", None

    await run_agent(
        session,
        user_id=user_id,
        request_id=new_id("req"),
        agent=AgentName.WORKFLOW,
        assignment="Organise Notion notes without completing assessed work",
        tool_name="organise-notes",
        work=work,
    )
    return {"organised": len(notes), "notes": [_note_dict(n) for n in notes]}


async def run_workflow(session: AsyncSession, user_id: str, name: str) -> dict[str, Any]:
    spec = next((w for w in WORKFLOWS if w["name"] == name), None)
    if spec is None:
        raise LookupError("unknown_workflow")
    now = clock.now()
    steps: list[dict[str, str]] = [{"bot": bot, "state": "passed"} for bot in spec["graph"]]
    result: dict[str, Any] = {"workflow": name}

    if name == "clarify-deadline":
        conflict = (
            (
                await session.execute(
                    select(ConflictingClaim).where(
                        ConflictingClaim.user_id == user_id, ConflictingClaim.resolution.is_(None)
                    )
                )
            )
            .scalars()
            .first()
        )
        if conflict is None or not conflict.clarification_draft:
            result["status"] = "nothing_to_clarify"
        else:
            drafted = await draft_email(
                session,
                user_id,
                "j.okonkwo@northbridge.example",
                f"Clarification: deadline conflict {conflict.obligation_id}",
                conflict.clarification_draft,
            )
            result.update(drafted)
    elif name == "organise-notes":
        result.update(await organise_notes(session, user_id))
    elif name == "slack-standup":
        drafted = await draft_email(
            session,
            user_id,
            "#csc0000-lab",
            "Standup draft",
            "Today: lab prep before 10:00. Blockers: deadline conflict on the problem set. "
            "This Slack draft has not been posted.",
            channel="slack",
        )
        result.update(drafted)
    elif name == "recruiting-brief":
        intern = (
            (
                await session.execute(
                    select(Obligation).where(
                        Obligation.user_id == user_id, Obligation.type == "recruiting"
                    )
                )
            )
            .scalars()
            .first()
        )
        result["brief"] = {
            "internship": intern.title if intern else "none",
            "due_at": intern.due_at.isoformat() if intern and intern.due_at else None,
            "linkedin": "fixture snapshot"
            if (await get_connection(session, user_id, "src_linkedin"))
            else None,
        }

    run = WorkflowRun(
        id=new_id("wfl"),
        user_id=user_id,
        name=name,
        state="passed",
        steps_json=steps,
        result_json=result,
        created_at=now,
        finished_at=clock.now(),
    )
    session.add(run)
    await record_audit(
        session,
        user_id=user_id,
        correlation_id=run.id,
        agent=AgentName.WORKFLOW.value,
        event_type="workflow_run",
        object_type="workflow",
        object_id=run.id,
        summary=spec["title"],
    )
    return {
        "id": run.id,
        "name": name,
        "title": spec["title"],
        "graph": spec["graph"],
        "state": run.state,
        "result": result,
    }


async def workspace_bundle(session: AsyncSession, user_id: str) -> dict[str, Any]:
    notes = (
        (await session.execute(select(WorkspaceNote).where(WorkspaceNote.user_id == user_id)))
        .scalars()
        .all()
    )
    messages = (
        (
            await session.execute(
                select(OutboundMessage)
                .where(OutboundMessage.user_id == user_id)
                .order_by(OutboundMessage.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    runs = (
        (
            await session.execute(
                select(WorkflowRun)
                .where(WorkflowRun.user_id == user_id)
                .order_by(WorkflowRun.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return {
        "live": True,
        "now": clock.now().isoformat(),
        "connectors": await list_connectors(session, user_id),
        "meetings": await meetings(session, user_id),
        "calendar": await calendar_week(session, user_id),
        "notes": [_note_dict(n) for n in notes],
        "messages": [
            {
                "id": m.id,
                "channel": m.channel,
                "to": m.to_address,
                "subject": m.subject,
                "state": m.state,
                "approval_id": m.approval_id,
                "sent_at": m.sent_at.isoformat() if m.sent_at else None,
            }
            for m in messages
        ],
        "workflows": WORKFLOWS,
        "workflow_runs": [
            {
                "id": r.id,
                "name": r.name,
                "state": r.state,
                "graph": r.steps_json,
                "result": r.result_json,
            }
            for r in runs
        ],
    }


def _note_dict(note: WorkspaceNote) -> dict[str, Any]:
    return {
        "id": note.id,
        "source": note.source,
        "title": note.title,
        "body": note.body,
        "tags": note.tags_json,
        "organised": note.organised,
    }
