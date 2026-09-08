"""Human-readable planning explanations without private chain-of-thought."""

from __future__ import annotations


def constraint_sentence(*, preferred: bool, buffer: bool, due_label: str) -> str:
    parts = [f"Scheduled before {due_label}", "no fixed event overlaps"]
    if preferred:
        parts.append("this is a preferred study period")
    if buffer:
        parts.append("it preserves a 24-hour deadline buffer")
    return "Scheduled because " + ", ".join(parts) + "."
