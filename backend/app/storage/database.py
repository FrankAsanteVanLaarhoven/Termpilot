"""Async SQLAlchemy engine and session factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.domain.models import Base
from app.settings import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_initialized = False


def _normalize_url(url: str) -> str:
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        url = _normalize_url(settings.resolved_database_url)
        connect_args: dict[str, object] = {}
        if url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
            if ":///" in url:
                raw_path = url.split(":///", 1)[1]
                if raw_path and raw_path != ":memory:" and not raw_path.startswith("file:"):
                    Path(raw_path).parent.mkdir(parents=True, exist_ok=True)
        elif "+asyncpg" in url and ("neon.tech" in url or settings.on_vercel):
            connect_args["ssl"] = True
        _engine = create_async_engine(url, echo=False, connect_args=connect_args, future=True)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(), expire_on_commit=False, class_=AsyncSession
        )
    return _session_factory


def _ensure_user_password_column(sync_conn: object) -> None:
    inspector = inspect(sync_conn)
    if "user_profiles" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("user_profiles")}
    alters = {
        "password_hash": "ALTER TABLE user_profiles ADD COLUMN password_hash VARCHAR(200)",
        "email_verified_at": "ALTER TABLE user_profiles ADD COLUMN email_verified_at DATETIME",
        "phone_e164": "ALTER TABLE user_profiles ADD COLUMN phone_e164 VARCHAR(20)",
        "phone_verified_at": "ALTER TABLE user_profiles ADD COLUMN phone_verified_at DATETIME",
        "mfa_sms_enabled": "ALTER TABLE user_profiles ADD COLUMN mfa_sms_enabled BOOLEAN DEFAULT 0",
    }
    for name, stmt in alters.items():
        if name not in columns:
            sync_conn.execute(text(stmt))  # type: ignore[union-attr]


async def init_db() -> None:
    global _initialized
    if _initialized:
        return
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_user_password_column)
    if "sqlite" in str(engine.url):
        try:
            async with engine.begin() as conn:
                await conn.execute(text("PRAGMA busy_timeout=5000"))
        except Exception:
            pass
    _initialized = True


async def drop_db() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def reset_engine() -> None:
    global _engine, _session_factory, _initialized
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
    _initialized = False


async def get_session() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    async with factory() as session:
        yield session
