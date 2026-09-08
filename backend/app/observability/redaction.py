"""Redact secrets and bulky private content from logs."""

from __future__ import annotations

import re
from typing import Any

_SECRET_KEYS = {
    "authorization",
    "api_key",
    "xai_api_key",
    "password",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "sentry_dsn",
    "otp",
    "code",
    "cookie",
    "session",
    "phone",
    "phone_e164",
    "code_hash",
    "token_hash",
    "password_hash",
}

_SECRET_RE = re.compile(r"(sk-|xai-|Bearer\s+)[A-Za-z0-9._\-]+", re.IGNORECASE)


def redact_text(value: str, limit: int = 240) -> str:
    cleaned = _SECRET_RE.sub("[REDACTED]", value)
    if len(cleaned) > limit:
        return cleaned[:limit] + "…"
    return cleaned


def redact_mapping(data: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in data.items():
        lowered = key.lower()
        if lowered in _SECRET_KEYS or "token" in lowered or "password" in lowered:
            out[key] = "[REDACTED]"
        elif key in {"email_body", "raw", "body", "content"} and isinstance(value, str):
            out[key] = f"[excerpt {len(value)} chars]"
        elif isinstance(value, dict):
            out[key] = redact_mapping(value)
        elif isinstance(value, str):
            out[key] = redact_text(value)
        else:
            out[key] = value
    return out
