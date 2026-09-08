"""Academic-integrity and privacy policy checks."""

from __future__ import annotations

import re

from app.domain.enums import GuardianDecision
from app.domain.schemas import GuardianVerdict

_HOMEWORK_PATTERNS = [
    re.compile(
        r"\b(write|complete|do|finish|submit)\b.{0,40}\b(essay|homework|assignment|exam)\b", re.I
    ),
    re.compile(r"answer (the|this|my) (quiz|exam|problem set)", re.I),
    re.compile(r"impersonat", re.I),
    re.compile(r"send (this|an email|a message) (to|as)", re.I),
    re.compile(r"log in as me", re.I),
    re.compile(r"collect (my )?(health|disability|medical)", re.I),
]


def inspect_user_goal(goal: str) -> GuardianVerdict:
    blocked: list[str] = []
    for pat in _HOMEWORK_PATTERNS:
        match = pat.search(goal)
        if match:
            blocked.append(match.group(0))
    if blocked:
        return GuardianVerdict(
            decision=GuardianDecision.BLOCK,
            reason_code="academic_integrity",
            summary=(
                "TermPilot organises work. It will not complete assessed work or impersonate you."
            ),
            blocked_actions=blocked,
        )
    return GuardianVerdict(
        decision=GuardianDecision.ALLOW,
        reason_code="goal_ok",
        summary="Goal is organisational and does not request assessed-work completion.",
    )


def inspect_source_text(text: str) -> GuardianVerdict:
    from app.policies.injection import find_injection_sentences

    hits = find_injection_sentences(text)
    if hits:
        return GuardianVerdict(
            decision=GuardianDecision.ESCALATE,
            reason_code="prompt_injection",
            summary="Untrusted source contained instruction-like text. Instructions were ignored.",
            blocked_actions=hits,
        )
    return GuardianVerdict(
        decision=GuardianDecision.ALLOW,
        reason_code="source_ok",
        summary="No instruction-like content detected.",
    )
