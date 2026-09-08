"""TermPilot FastAPI application."""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.observability.logging import configure_logging, get_logger
from app.services import clock
from app.services.demo import reset_demo
from app.settings import get_settings
from app.storage.database import init_db

log = get_logger("termpilot.api")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    settings = get_settings()
    try:
        await init_db()
    except Exception as exc:  # noqa: BLE001
        # A startup crash becomes FUNCTION_INVOCATION_FAILED on Vercel.
        log.warning("init_db_skipped", error=str(exc))
    if settings.env == "demo" and not settings.on_vercel:
        try:
            await reset_demo()
        except Exception as exc:  # noqa: BLE001
            log.warning("demo_seed_skipped", error=str(exc))
    if settings.sentry_dsn:
        try:
            import sentry_sdk

            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                traces_sample_rate=settings.sentry_traces_sample_rate,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("sentry_init_failed", error=str(exc))
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="TermPilot",
        version="0.1.0",
        description="Verified control tower for student life.",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=r"https://([a-z0-9-]+\.)*vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/health")
    @application.get("/api/health")
    async def health() -> dict[str, object]:
        return {
            "status": "ok",
            "service": "termpilot",
            "mode": settings.env,
            "grok": settings.grok_connection_state,
            "time": clock.now().isoformat(),
            "access_code_required": bool(settings.access_code),
            "student_login": True,
            "password_required": True,
            "email_verification": settings.codes_required,
            "mfa": settings.codes_required,
            "mail": "resend" if settings.resend_api_key else "unset",
            "mail_from": settings.auth_from_email,
            "origin": "FAVL-TP-D88A5B6D3CD1",
        }

    load_error: str | None = None
    try:
        from app.api.auth_routes import router as auth_router
        from app.api.ops import ops
        from app.api.router import router

        application.include_router(auth_router)
        application.include_router(router)
        application.include_router(ops)
        application.include_router(auth_router, prefix="/api", include_in_schema=False)
        application.include_router(router, prefix="/api", include_in_schema=False)
        application.include_router(ops, prefix="/api", include_in_schema=False)
    except Exception as exc:  # noqa: BLE001
        load_error = f"{type(exc).__name__}: {exc}"[:400]
        log.warning("routers_unavailable", error=load_error)

        @application.api_route(
            "/{full_path:path}",
            methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        )
        async def routers_unavailable(full_path: str) -> JSONResponse:
            if full_path in {"health", "api/health"}:
                return JSONResponse({"status": "degraded", "service": "termpilot", "detail": load_error})
            return JSONResponse(
                {"detail": f"TermPilot API failed to load: {load_error}"},
                status_code=503,
            )

    hits: dict[str, int] = {}

    @application.exception_handler(Exception)
    async def unhandled_error(_request: Request, exc: Exception) -> JSONResponse:
        log.warning("unhandled_error", error=type(exc).__name__, detail=str(exc)[:240])
        return JSONResponse(
            {"detail": "TermPilot hit a server error. Wait a moment and try again."},
            status_code=500,
        )

    @application.middleware("http")
    async def add_correlation(request: Request, call_next):  # type: ignore[no-untyped-def]
        ip = request.client.host if request.client else "local"
        hits[ip] = hits.get(ip, 0) + 1
        if hits[ip] > 20000:
            return JSONResponse(
                {"router": {"code": "rate_limited", "route": "backoff"}}, status_code=429
            )
        try:
            response = await call_next(request)
        except Exception as exc:  # noqa: BLE001
            log.warning("request_crash", error=type(exc).__name__, detail=str(exc)[:240])
            response = JSONResponse(
                {"detail": "TermPilot hit a server error. Wait a moment and try again."},
                status_code=500,
            )
        response.headers["X-TermPilot"] = "termpilot"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(self), geolocation=(), display-capture=()"
        )
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    return application


app = create_app()
