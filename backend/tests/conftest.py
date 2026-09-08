from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("TERMPILOT_ENV", "test")
os.environ.setdefault("GROK_MODE", "fake")
os.environ.setdefault("TERMPILOT_NOW", "2026-09-05T08:00:00+01:00")
os.environ.setdefault("XAI_API_KEY", "")

from app.settings import reset_settings_cache
from app.storage.database import reset_engine


@pytest.fixture
async def client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    db_path = tmp_path / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["TERMPILOT_ENV"] = "test"
    os.environ["GROK_MODE"] = "fake"
    reset_settings_cache()
    await reset_engine()
    from app.main import create_app
    from app.storage.database import init_db

    await init_db()
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
    await reset_engine()
    reset_settings_cache()
