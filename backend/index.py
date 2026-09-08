"""Vercel FastAPI entry. Health never imports the heavy app stack."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

app = FastAPI(title="TermPilot")
_full = None


def _full_app():
    global _full
    if _full is None:
        from app.main import app as inner

        _full = inner
    return _full


@app.get("/health")
@app.get("/api/health")
async def health() -> dict[str, object]:
    mail = "unset"
    mail_from = "TermPilot <student@termpilot.org>"
    codes = False
    try:
        from app.settings import get_settings

        settings = get_settings()
        mail = "resend" if settings.resend_api_key else "unset"
        mail_from = settings.auth_from_email
        codes = settings.codes_required
    except Exception:
        pass
    return {
        "status": "ok",
        "service": "termpilot",
        "boot": "index",
        "student_login": True,
        "password_required": True,
        "email_verification": codes,
        "mfa": codes,
        "mail": mail,
        "mail_from": mail_from,
    }


@app.api_route(
    "/{full_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def forward(full_path: str, request: Request) -> Response:
    try:
        inner = _full_app()
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            {"detail": f"TermPilot API failed to load: {type(exc).__name__}: {exc}"[:400]},
            status_code=503,
        )
    from httpx import ASGITransport, AsyncClient

    stripped = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {"host", "content-length"}
    }
    async with AsyncClient(transport=ASGITransport(app=inner), base_url="http://termpilot") as client:
        upstream = await client.request(
            request.method,
            request.url.path + (f"?{request.url.query}" if request.url.query else ""),
            content=await request.body(),
            headers=stripped,
            cookies=request.cookies,
        )
    skipped = {"content-encoding", "content-length", "transfer-encoding", "connection"}
    headers = {k: v for k, v in upstream.headers.items() if k.lower() not in skipped}
    return Response(content=upstream.content, status_code=upstream.status_code, headers=headers)
