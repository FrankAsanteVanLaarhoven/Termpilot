"""Grok Bot is TermPilot's student-facing engine.

It does not train a second bot. Every student feature is a named tool
Grok Bot can open or execute through existing services. Guardian, Verifier
and on-screen approvals are never bypassed. Spoken yes is never a write.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.policies.consent import ConsentError
from app.policies.gate import apply_student_policies

# Student-facing tools Grok Bot can operate. Proof-only agent ops stay out.
STUDENT_TOOLS: list[dict[str, Any]] = [
    {
        "id": "open_tower",
        "label": "My week",
        "view": "tower",
        "kind": "open",
        "writes": False,
        "phrases": ("open tower", "control tower", "show my week", "open my week", "my week"),
    },
    {
        "id": "open_workspace",
        "label": "Workspace",
        "view": "workspace",
        "kind": "open",
        "writes": False,
        "phrases": ("open workspace", "my workspace", "show workspace", "show notes"),
    },
    {
        "id": "organise_notes",
        "label": "Organise notes",
        "view": "workspace",
        "kind": "execute",
        "writes": False,
        "phrases": ("organise notes", "organize notes", "file my notes", "organise my notes"),
    },
    {
        "id": "open_connectors",
        "label": "Connected services",
        "view": "sources",
        "kind": "open",
        "writes": False,
        "phrases": ("open connectors", "connected services", "show connectors", "link accounts"),
    },
    {
        "id": "connect_all",
        "label": "Connect all",
        "view": "sources",
        "kind": "execute",
        "writes": False,
        "phrases": ("connect all", "connect my accounts", "connect everything"),
    },
    {
        "id": "connect_university_mail",
        "label": "Connect university email",
        "view": "sources",
        "kind": "execute",
        "writes": False,
        "phrases": (
            "connect university email",
            "connect my email",
            "connect my university email",
            "link my mailbox",
            "connect gmail",
            "connect outlook",
        ),
    },
    {
        "id": "connect_service",
        "label": "Connect a service",
        "view": "sources",
        "kind": "execute",
        "writes": False,
        "phrases": (
            "connect github",
            "connect git hub",
            "connect jira",
            "connect notion",
            "connect slack",
            "connect linkedin",
            "connect discord",
            "connect teams",
            "connect google drive",
            "connect drive",
            "connect orcid",
        ),
    },
    {
        "id": "open_workflows",
        "label": "Automations",
        "view": "workflows",
        "kind": "open",
        "writes": False,
        "phrases": ("open workflows", "show automations", "automations", "show workflows"),
    },
    {
        "id": "run_workflow",
        "label": "Run a workflow",
        "view": "workflows",
        "kind": "execute",
        "writes": False,
        "phrases": (
            "run standup",
            "slack standup",
            "run workflow",
            "clarify deadline",
            "recruiting brief",
        ),
    },
    {
        "id": "open_obligations",
        "label": "Deadlines and tasks",
        "view": "obligations",
        "kind": "open",
        "writes": False,
        "phrases": ("open obligations", "show obligations", "my tasks", "show tasks"),
    },
    {
        "id": "open_timeline",
        "label": "Schedule",
        "view": "timeline",
        "kind": "open",
        "writes": False,
        "phrases": ("open timeline", "show timeline", "my schedule", "show schedule"),
    },
    {
        "id": "open_evidence",
        "label": "Why TermPilot says this",
        "view": "evidence",
        "kind": "open",
        "writes": False,
        "phrases": ("open evidence", "show evidence", "why do you say", "provenance"),
    },
    {
        "id": "open_impact",
        "label": "My progress",
        "view": "impact",
        "kind": "open",
        "writes": False,
        "phrases": ("open impact", "my progress", "show impact"),
    },
    {
        "id": "open_settings",
        "label": "Preferences",
        "view": "settings",
        "kind": "open",
        "writes": False,
        "phrases": ("open settings", "preferences", "show settings"),
    },
    {
        "id": "open_help",
        "label": "Help",
        "view": "help",
        "kind": "open",
        "writes": False,
        "phrases": ("open help", "how does this work", "show help"),
    },
    {
        "id": "open_chat",
        "label": "Chat",
        "view": "chat",
        "kind": "open",
        "writes": False,
        "phrases": ("open chat", "back to chat"),
    },
    {
        "id": "weather",
        "label": "7-day forecast",
        "view": "tower",
        "kind": "execute",
        "writes": False,
        "phrases": ("weather", "forecast", "will it rain"),
    },
    {
        "id": "world_clock",
        "label": "World clock",
        "view": "tower",
        "kind": "execute",
        "writes": False,
        "phrases": ("world clock", "what time is it", "time zones"),
    },
    {
        "id": "open_calendar",
        "label": "Calendar",
        "view": "calendar",
        "kind": "open",
        "writes": False,
        "phrases": ("open calendar", "show calendar", "my calendar"),
    },
    {
        "id": "open_conflicts",
        "label": "Conflicts",
        "view": "conflicts",
        "kind": "open",
        "writes": False,
        "phrases": ("open conflicts", "show conflicts", "deadline conflict"),
    },
    {
        "id": "open_approvals",
        "label": "Approvals",
        "view": "approvals",
        "kind": "open",
        "writes": False,
        "phrases": ("open approvals", "show approvals", "pending approval"),
    },
    {
        "id": "open_news",
        "label": "Student news",
        "view": "news",
        "kind": "open",
        "writes": False,
        "phrases": ("open news", "show news", "newsfeed", "student union"),
    },
    {
        "id": "open_mailbox",
        "label": "Mailbox",
        "view": "mailbox",
        "kind": "open",
        "writes": False,
        "phrases": ("open mailbox", "open inbox", "mail desk", "show mailbox"),
    },
    {
        "id": "reconcile",
        "label": "Reconcile sources",
        "view": "conflicts",
        "kind": "execute",
        "writes": False,
        "phrases": ("reconcile", "scan my sources", "check my deadlines"),
    },
]


def catalog() -> dict[str, Any]:
    return {
        "engine": "grok_bot",
        "product": "TermPilot",
        "claim": (
            "Grok Bot operates every student-facing TermPilot tool. "
            "No second bot is trained. Guardian, Verifier and on-screen approvals stay in force."
        ),
        "writes_without_approval": False,
        "spoken_yes_writes": False,
        "tools": [
            {
                "id": row["id"],
                "label": row["label"],
                "view": row["view"],
                "kind": row["kind"],
                "writes": row["writes"],
            }
            for row in STUDENT_TOOLS
        ],
        "policies": [
            "guardian_blocks_assessed_work",
            "verifier_owns_conflicts",
            "on_screen_approval_for_writes",
            "spoken_yes_is_not_a_write",
            "no_invented_deadlines",
        ],
        "also_via_voicebridge": [
            "week",
            "conflict",
            "reschedule",
            "mailbox",
            "mailbox_cleanup",
            "mailbox_alerts",
            "mailbox_draft",
            "support",
            "switch_language",
        ],
    }


def classify_tool(lowered: str) -> str | None:
    ranked: list[tuple[int, str, str]] = []
    for row in STUDENT_TOOLS:
        for phrase in row["phrases"]:
            if phrase in lowered:
                ranked.append((len(phrase), phrase, row["id"]))
    if not ranked:
        return None
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][2]


def _connectors_from_text(text: str) -> list[str]:
    lowered = text.lower()
    mapping: list[tuple[tuple[str, ...], list[str]]] = [
        (("github", "git hub"), ["src_github"]),
        (("jira",), ["src_jira"]),
        (("notion",), ["src_notion"]),
        (("slack",), ["src_slack"]),
        (("linkedin",), ["src_linkedin"]),
        (("discord",), ["src_discord"]),
        (("teams",), ["src_teams"]),
        (("google drive", "gdrive", "drive"), ["src_gdrive"]),
        (("orcid",), ["src_orcid"]),
        (("gmail", "outlook", "university email", "mailbox"), ["src_email", "src_mailbox"]),
    ]
    found: list[str] = []
    for phrases, ids in mapping:
        if any(phrase in lowered for phrase in phrases):
            for connector_id in ids:
                if connector_id not in found:
                    found.append(connector_id)
    return found


def _workflow_name(text: str) -> str:
    lowered = text.lower()
    if "note" in lowered or "notion" in lowered:
        return "organise-notes"
    if "standup" in lowered or "slack" in lowered:
        return "slack-standup"
    if "recruit" in lowered:
        return "recruiting-brief"
    return "clarify-deadline"


async def execute_tool(
    session: AsyncSession,
    user_id: str,
    intent: str,
    text: str,
) -> tuple[str, dict[str, Any], bool]:
    """Run a Grok Bot tool through existing services. Never writes calendars or mail."""
    text, policy = apply_student_policies(text)
    if policy.get("blocked"):
        return (str(policy.get("summary") or "Blocked by Guardian."), policy, True)

    tool = next((row for row in STUDENT_TOOLS if row["id"] == intent), None)
    if tool is None:
        return ("I do not have that tool.", {"action": "none", "engine": "grok_bot"}, False)

    facts: dict[str, Any] = {
        "open_view": tool["view"],
        "tool": intent,
        **policy,
        "writes": False,
    }
    requires_screen = True

    if intent == "connect_all":
        from app.services.demo import prepare_student_workspace

        result = await prepare_student_workspace(session, user_id)
        facts.update(result)
        facts["one_click"] = True
        facts["open_view"] = "sources"
        spoken = (
            f"Connected {result.get('connected', 0)} services Grok Bot can already use. "
            f"{result.get('obligations', 0)} obligations are on your week. "
            "Opening connected services. Calendar and mail still wait for on-screen approval."
        )
        return spoken, facts, True

    if intent == "connect_university_mail":
        from app.services.workspace import connect_all

        result = await connect_all(session, user_id, ["src_email", "src_mailbox"])
        facts.update(result)
        facts["open_view"] = "sources"
        facts["one_click"] = True
        spoken = (
            "University email and student inbox are connected in one click. "
            "Live Gmail/Outlook is optional when provider keys are set. "
            "Until then Grok Bot reads the consented demo mailbox. Nothing is sent without approval."
        )
        return spoken, facts, True

    if intent == "connect_service":
        from app.services.workspace import connect_all

        wanted = _connectors_from_text(text)
        result = await connect_all(session, user_id, wanted or None)
        facts.update(result)
        facts["one_click"] = True
        facts["open_view"] = "sources"
        names = ", ".join(wanted) if wanted else "your services"
        spoken = (
            f"Connected {result.get('count', 0)} service(s) in one click ({names}). "
            "Opening connected services. Calendar and mail still wait for on-screen approval."
        )
        return spoken, facts, True

    if intent == "organise_notes":
        from app.services.workspace import organise_notes

        try:
            result = await organise_notes(session, user_id)
        except ConsentError as exc:
            return (
                "Connect Notion first so I can file notes you already own. "
                f"({exc.code}) I will not invent notes.",
                {**facts, "open_view": "sources", "action": "none"},
                True,
            )
        facts.update(result)
        spoken = (
            f"Filed {result.get('organised', 0)} notes. "
            "Assessed work was tagged as reference only — I did not complete it."
        )
        return spoken, facts, True

    if intent == "run_workflow":
        from app.services.workspace import run_workflow

        name = _workflow_name(text)
        try:
            result = await run_workflow(session, user_id, name)
        except (ConsentError, LookupError) as exc:
            code = getattr(exc, "code", type(exc).__name__)
            return (
                f"I could not run {name} ({code}). Opening automations. "
                "Nothing was sent.",
                {**facts, "action": "none", "workflow": name},
                True,
            )
        facts.update(result)
        spoken = (
            f"Ran {name} through the existing workflow graph. "
            "If a message was drafted it is unsent until you approve it on screen."
        )
        return spoken, facts, True

    if intent == "weather":
        from app.services.world import weather_week

        try:
            weather = await weather_week()
        except Exception:  # noqa: BLE001
            weather = {"stale": True, "place": "London", "source": "unavailable"}
        facts["weather"] = weather
        days = weather.get("days") or []
        first = days[0] if days else None
        if first:
            spoken = (
                f"London forecast via Open-Meteo: {first.get('label')} "
                f"{first.get('tmax')}° / {first.get('tmin')}°. Opening your week widgets."
            )
        else:
            spoken = "Opening your week so you can see the forecast widget. Live weather was unavailable."
        return spoken, facts, True

    if intent == "world_clock":
        from app.services.world import world_clock

        clock_pack = world_clock()
        facts["world_clock"] = clock_pack
        first = (clock_pack.get("items") or [{}])[0]
        spoken = (
            f"{first.get('label', 'London')} is {first.get('time', '—')}. "
            "Opening your week widgets for the full world clock."
        )
        return spoken, facts, True

    if intent == "reconcile":
        spoken = (
            "Handing this to the Orchestrator. Guardian and Verifier stay in the path. "
            "I will not write the calendar until you approve on screen."
        )
        facts["handoff"] = "orchestrator"
        return spoken, facts, True

    spoken = (
        f"Opening {tool['label']}. Grok Bot is using the TermPilot tool that already exists — "
        "I am not a second trained bot. Calendar and mail still wait for on-screen approval."
    )
    return spoken, facts, requires_screen


async def answer_with_policies(
    session: AsyncSession,
    user_id: str,
    text: str,
) -> tuple[str, dict[str, Any], bool]:
    """Free-form Grok Bot reply grounded in TermPilot facts and Guardian."""
    import json

    from app.agents.grok_client import GrokUnavailableError, get_grok_adapter
    from app.agents.prompts import GROKBOT_REPLY_PROMPT
    from app.services import clock
    from app.services.queries import attention_queue, control_tower

    text, policy = apply_student_policies(text)
    if policy.get("blocked"):
        return (str(policy.get("summary") or "Blocked by Guardian."), policy, True)

    tower = await control_tower(session, user_id)
    if tower.verified_obligations == 0 and tower.open_conflicts == 0:
        from app.services.demo import prepare_student_workspace

        await prepare_student_workspace(session, user_id)
        tower = await control_tower(session, user_id)
    queue = await attention_queue(session, user_id)
    adapter = get_grok_adapter()
    facts: dict[str, Any] = {
        **policy,
        "adapter": adapter.mode,
        "open_view": "tower" if tower.open_conflicts or tower.pending_approvals else "chat",
        "writes": False,
    }
    snapshot = {
        "question": text[:2000],
        "now": clock.now().isoformat(),
        "readiness": tower.readiness,
        "verified_obligations": tower.verified_obligations,
        "open_conflicts": tower.open_conflicts,
        "pending_approvals": tower.pending_approvals,
        "plan_feasible": tower.plan_feasible,
        "attention": queue[:6],
        "tools": [row["id"] for row in STUDENT_TOOLS],
    }

    if adapter.mode == "live":
        try:
            raw = await adapter.complete_json(
                GROKBOT_REPLY_PROMPT,
                json.dumps(snapshot, default=str)[:8000],
                "grokbot-reply",
            )
            spoken = str(raw.get("spoken") or "").strip()[:2000]
            view = raw.get("open_view")
            allowed = {row["view"] for row in STUDENT_TOOLS} | {"chat", "help"}
            if isinstance(view, str) and view in allowed:
                facts["open_view"] = view
            tool_id = raw.get("tool")
            if isinstance(tool_id, str) and any(row["id"] == tool_id for row in STUDENT_TOOLS):
                return await execute_tool(session, user_id, tool_id, text)
            if spoken:
                facts["live"] = True
                return spoken, facts, True
        except (GrokUnavailableError, Exception):  # noqa: BLE001
            facts["adapter"] = "fake"

    spoken = (
        "Grok Bot here — using TermPilot's verified tower, not a second trained bot. "
        f"Readiness {tower.readiness}. {tower.verified_obligations} verified obligations, "
        f"{tower.open_conflicts} open conflicts, {tower.pending_approvals} pending approvals. "
        "I will not invent a deadline or write your calendar. "
        "Ask me to reconcile, open mail, or review conflicts and I will use the existing tool."
    )
    return spoken, facts, True
