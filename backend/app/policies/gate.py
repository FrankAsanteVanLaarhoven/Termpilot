"""Single policy gate for student-facing Grok Bot turns."""

from __future__ import annotations

from typing import Any

from app.policies.injection import strip_injected_instructions
from app.policies.integrity import inspect_user_goal


def apply_student_policies(text: str) -> tuple[str, dict[str, Any]]:
    cleaned, hits = strip_injected_instructions(text)
    verdict = inspect_user_goal(cleaned)
    facts: dict[str, Any] = {
        "engine": "grok_bot",
        "policy": "guardian+injection+approval",
        "blocked": verdict.decision.value == "block",
        "reason_code": verdict.reason_code,
        "writes": False,
        "spoken_yes_writes": False,
    }
    if hits:
        facts["injection_stripped"] = hits
    if facts["blocked"]:
        facts["action"] = "none"
        facts["open_view"] = "help"
        facts["summary"] = verdict.summary
    return cleaned, facts
