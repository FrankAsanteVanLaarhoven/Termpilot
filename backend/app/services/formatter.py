"""Clean extracted text before storage or export. Never persist raw HTML mail."""

from __future__ import annotations

import hashlib
import hmac
import re
from typing import Any

_TAG = re.compile(r"<[^>]+>", re.I)
_WS = re.compile(r"\s+")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PEPPER = b"termpilot-governance-v1"


def strip_html(value: str) -> str:
    cleaned = _TAG.sub(" ", value)
    return _WS.sub(" ", cleaned).strip()


def hash_identifier(value: str) -> str:
    digest = hmac.new(_PEPPER, value.strip().lower().encode("utf-8"), hashlib.sha256).hexdigest()
    return f"h_{digest[:32]}"


def redact_emails(value: str) -> str:
    return _EMAIL.sub("[email-hash]", value)


def format_record(payload: dict[str, Any], *, hash_pii: bool = True) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in payload.items():
        if key in {"body", "excerpt", "summary", "title", "subject"} and isinstance(value, str):
            text = strip_html(value)
            text = redact_emails(text) if hash_pii else text
            out[key] = text[:800]
        elif key in {"from", "to", "email", "to_address", "from_address"} and isinstance(value, str):
            out[key] = hash_identifier(value) if hash_pii else value
        elif isinstance(value, dict):
            out[key] = format_record(value, hash_pii=hash_pii)
        else:
            out[key] = value
    out["_formatted"] = True
    out["_pii_hashed"] = hash_pii
    return out


def payload_digest(payload: dict[str, Any]) -> str:
    blob = repr(sorted(payload.items())).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()
