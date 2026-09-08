"""Grok-native LLM routing with optional OpenRouter and student-owned keys.

TermPilot always prefers xAI Grok. Other models are listed so the student
knows what the bot is doing; Max-tier rows stay locked unless a student
OpenRouter key is supplied on the request. Keys are never written to Postgres.
"""

from __future__ import annotations

from typing import Any

from app.settings import get_settings

MODES = [
    {"id": "chat", "label": "Chat", "does": "Conversational help. No calendar writes."},
    {"id": "work", "label": "Work", "does": "Student ops: deadlines, conflicts, plans, approvals."},
    {"id": "computer", "label": "Computer", "does": "Use connected tools (mail, calendar, news) with Guardian."},
]

TOOLS = [
    {"id": "search", "label": "Search", "locked": False, "does": "Search authorised TermPilot sources."},
    {"id": "deep_research", "label": "Deep research", "locked": False, "does": "Cross-check news, mail and obligations."},
    {
        "id": "model_council",
        "label": "Model council",
        "badge": "Max",
        "locked": True,
        "does": "Multi-model vote. Locked unless a student OpenRouter key is present.",
    },
    {"id": "learn", "label": "Learn step by step", "locked": False, "does": "Explain a plan without completing assessed work."},
]

MODELS = [
    {
        "id": "best",
        "label": "Best",
        "blurb": "Selects the best available model",
        "provider": "grok",
        "route": "native",
        "locked": False,
    },
    {
        "id": "sonar-2",
        "label": "Sonar 2",
        "blurb": "OpenRouter search-style model",
        "provider": "openrouter",
        "route": "perplexity/sonar",
        "locked": False,
    },
    {
        "id": "gpt-5.6-terra",
        "label": "GPT-5.6 Terra",
        "blurb": "OpenRouter",
        "provider": "openrouter",
        "route": "openai/gpt-5",
        "locked": False,
    },
    {
        "id": "gpt-5.6-sol",
        "label": "GPT-5.6 Sol",
        "blurb": "Max tier",
        "provider": "openrouter",
        "route": "openai/gpt-5",
        "locked": True,
        "badge": "Max",
    },
    {
        "id": "gemini-3.8-flash",
        "label": "Gemini 3.8 Flash",
        "blurb": "OpenRouter",
        "provider": "openrouter",
        "route": "google/gemini-2.5-flash",
        "locked": False,
    },
    {
        "id": "claude-sonnet-5",
        "label": "Claude Sonnet 5",
        "blurb": "OpenRouter",
        "provider": "openrouter",
        "route": "anthropic/claude-sonnet-4",
        "locked": False,
    },
    {
        "id": "claude-opus-5",
        "label": "Claude Opus 5",
        "blurb": "Max tier",
        "provider": "openrouter",
        "route": "anthropic/claude-opus-4",
        "locked": True,
        "badge": "Max",
    },
    {
        "id": "kimi-k3-thinking",
        "label": "Kimi K3 Thinking",
        "blurb": "OpenRouter",
        "provider": "openrouter",
        "route": "moonshotai/kimi-k2",
        "locked": False,
    },
    {
        "id": "glm-5.3-thinking",
        "label": "GLM 5.3 Thinking",
        "blurb": "New",
        "provider": "openrouter",
        "route": "z-ai/glm-4.5",
        "locked": False,
        "badge": "New",
    },
    {
        "id": "grok-4.6",
        "label": "Grok 4.6",
        "blurb": "Native xAI",
        "provider": "grok",
        "route": "native",
        "locked": False,
    },
    {
        "id": "nemotron-3-ultra",
        "label": "Nemotron 3 Ultra Thinking",
        "blurb": "OpenRouter",
        "provider": "openrouter",
        "route": "nvidia/llama-3.1-nemotron-70b-instruct",
        "locked": False,
    },
]


def catalog(*, student_openrouter: bool = False, student_xai: bool = False) -> dict[str, Any]:
    settings = get_settings()
    grok_live = settings.use_live_grok or student_xai
    openrouter = bool(settings.openrouter_api_key) or student_openrouter
    models = []
    for row in MODELS:
        locked = bool(row.get("locked"))
        if row["provider"] == "openrouter" and not openrouter:
            locked = True
        if row["provider"] == "grok" and not grok_live and row["id"] != "best":
            pass
        models.append({**row, "locked": locked, "available": not locked})
    return {
        "native": "grok",
        "grok_state": settings.grok_connection_state,
        "openrouter": openrouter,
        "student_keys_accepted": True,
        "keys_persisted": False,
        "modes": MODES,
        "tools": [
            {**tool, "locked": bool(tool["locked"]) and not student_openrouter}
            for tool in TOOLS
        ],
        "models": models,
        "note": (
            "Grok is native. Other names are routed through OpenRouter only when you "
            "or the platform supply a key. Max rows stay locked. Keys are not stored in Postgres."
        ),
    }


def resolve(model_id: str, *, student_openrouter: bool = False) -> dict[str, Any]:
    pack = catalog(student_openrouter=student_openrouter)
    chosen = next((row for row in pack["models"] if row["id"] == model_id), pack["models"][0])
    if chosen["id"] == "best":
        chosen = next(row for row in pack["models"] if row["id"] == "grok-4.6")
    if chosen.get("locked"):
        return {
            "ok": False,
            "reason": "locked",
            "fallback": "grok-4.6",
            "provider": "grok",
            "mode": pack["grok_state"],
        }
    return {
        "ok": True,
        "id": chosen["id"],
        "label": chosen["label"],
        "provider": chosen["provider"],
        "route": chosen["route"],
        "mode": pack["grok_state"] if chosen["provider"] == "grok" else "openrouter",
    }
