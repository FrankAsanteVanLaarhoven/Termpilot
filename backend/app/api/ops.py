"""Production ops: export, privacy, LLM catalog, WebRTC signalling, SDK."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id, db_session
from app.policies.consent import ConsentError
from app.services.exporting import DESTINATIONS, next_page_url, send_export
from app.services.formatter import format_record, hash_identifier, strip_html
from app.services.llm import catalog, resolve
from app.services.privacy_gov import (
    cache_policy,
    cookie_banner,
    list_policies,
    record_cookie_choice,
)

ops = APIRouter()

_RTC: dict[str, list[dict[str, Any]]] = {}
_RATE: dict[str, int] = {}


class ExportIn(BaseModel):
    destination: str = "json"
    target: str = ""


class CookieIn(BaseModel):
    analytics: bool = False
    export: bool = False


class PolicyIn(BaseModel):
    title: str
    body: str
    approved: bool = True


class FormatIn(BaseModel):
    text: str = ""
    payload: dict[str, Any] | None = None


class RtcIn(BaseModel):
    kind: str
    payload: dict[str, Any]


@ops.get("/llm/catalog")
async def llm_catalog(
    x_openrouter_key: str | None = Header(default=None, alias="X-OpenRouter-Key"),
    x_xai_key: str | None = Header(default=None, alias="X-XAI-Key"),
) -> dict[str, Any]:
    return catalog(student_openrouter=bool(x_openrouter_key), student_xai=bool(x_xai_key))


@ops.post("/llm/resolve")
async def llm_resolve(
    model_id: str = "best",
    x_openrouter_key: str | None = Header(default=None, alias="X-OpenRouter-Key"),
) -> dict[str, Any]:
    return resolve(model_id, student_openrouter=bool(x_openrouter_key))


@ops.post("/export")
async def post_export(
    body: ExportIn,
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    try:
        return await send_export(session, user_id, body.destination, body.target)
    except ConsentError as exc:
        raise HTTPException(403, exc.code) from exc


@ops.get("/export/destinations")
async def export_destinations() -> dict[str, Any]:
    return {"destinations": DESTINATIONS, "raw_bodies": False, "scrape": False}


@ops.post("/data/format")
async def data_format(body: FormatIn) -> dict[str, Any]:
    if body.payload is not None:
        return format_record(body.payload)
    return {"text": strip_html(body.text), "hashed": hash_identifier(body.text) if body.text else ""}


@ops.get("/privacy/cookies")
async def get_cookies() -> dict[str, Any]:
    return cookie_banner()


@ops.post("/privacy/cookies")
async def post_cookies(
    body: CookieIn,
    session: AsyncSession = Depends(db_session),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    return await record_cookie_choice(session, user_id, True, body.analytics, body.export)


@ops.post("/privacy/policy")
async def post_policy(
    body: PolicyIn,
    session: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    return await cache_policy(session, body.title, body.body, body.approved)


@ops.get("/privacy/policy")
async def get_policies(session: AsyncSession = Depends(db_session)) -> dict[str, Any]:
    return {"items": await list_policies(session), "raw_policy_text_stored": False}


@ops.post("/feeds/next")
async def feed_next(body: dict[str, str]) -> dict[str, Any]:
    url = next_page_url(body.get("document", ""))
    return {
        "next": url,
        "continue": bool(url),
        "note": "Public feed pagination only. University portals are not scraped.",
    }


@ops.post("/rtc/{room}")
async def rtc_post(room: str, body: RtcIn) -> dict[str, Any]:
    _RTC.setdefault(room, []).append({"kind": body.kind, "payload": body.payload})
    _RTC[room] = _RTC[room][-20:]
    return {"ok": True, "queued": len(_RTC[room]), "media_retained": False}


@ops.get("/rtc/{room}")
async def rtc_get(room: str) -> dict[str, Any]:
    items = _RTC.pop(room, [])
    return {"items": items, "media_retained": False}


@ops.get("/sdk/termpilot.py", response_class=PlainTextResponse)
async def sdk_python() -> str:
    return SDK_PY


SDK_PY = '''"""TermPilot offline/read-only SDK. Does not send mail or write calendars."""
from __future__ import annotations
import json, urllib.request

class TermPilot:
    def __init__(self, base="http://127.0.0.1:8000"):
        self.base = base.rstrip("/")

    def _get(self, path):
        with urllib.request.urlopen(self.base + path) as r:
            return json.load(r)

    def health(self):
        return self._get("/health")

    def tower(self):
        return self._get("/tower")

    def catalog(self):
        return self._get("/llm/catalog")
'''
