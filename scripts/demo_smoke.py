#!/usr/bin/env python3
"""Run the frozen demo path five times. Exit 1 on any failure."""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

GOAL = (
    "TermPilot, reconcile my academic and recruiting commitments for the next 14 days. "
    "Show conflicts, build a realistic plan around my 20-hour weekly limit, "
    "and ask before changing my calendar."
)


async def run_once(index: int) -> None:
    from httpx import ASGITransport, AsyncClient

    from app.main import create_app
    from app.settings import reset_settings_cache
    from app.storage.database import init_db, reset_engine

    tmp = Path(tempfile.mkdtemp()) / f"smoke-{index}.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{tmp}"
    os.environ["TERMPILOT_ENV"] = "test"
    os.environ["GROK_MODE"] = "fake"
    os.environ["TERMPILOT_NOW"] = "2026-09-05T08:00:00+01:00"
    reset_settings_cache()
    await reset_engine()
    await init_db()
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reset = await client.post("/demo/reset")
        assert reset.status_code == 200, reset.text
        before = await client.get("/calendar")
        before_n = len(before.json()["items"])
        cmd = await client.post("/command", json={"text": GOAL})
        assert cmd.status_code == 200, cmd.text
        body = cmd.json()
        obs = await client.get("/obligations")
        items = obs.json()["items"]
        titles = {o["title"] for o in items}
        assert len(items) == 6, titles
        assert "Robotics Lab Report" in titles
        lab = next(o for o in items if o["title"] == "Robotics Lab Report")
        detail = await client.get(f"/obligations/{lab['obligation_id']}")
        assert len(detail.json()["claims"]) >= 2
        problem = next(o for o in items if o["title"] == "Control Systems Problem Set")
        assert problem["verification_state"] == "conflicted"
        reading = next(o for o in items if o["title"] == "Weekly Reading Response")
        assert reading["verification_state"] == "needs_review"
        conflicts = await client.get("/conflicts")
        assert conflicts.json()["items"]
        audit = await client.get("/audit-events")
        types = {e["event_type"] for e in audit.json()["items"]}
        assert "prompt_injection_ignored" in types
        mid = await client.get("/calendar")
        assert len(mid.json()["items"]) == before_n
        approvals = await client.get("/approvals")
        pending = [a for a in approvals.json()["items"] if a["state"] == "pending"]
        assert pending
        approval_id = pending[0]["id"]
        blocked = await client.post("/calendar/apply", params={"approval_id": approval_id})
        assert blocked.status_code == 409
        approved = await client.post(f"/approvals/{approval_id}/approve")
        assert approved.status_code == 200
        applied = await client.post("/calendar/apply", params={"approval_id": approval_id})
        assert applied.status_code == 200
        replay = await client.post("/calendar/apply", params={"approval_id": approval_id})
        assert replay.json()["status"] == "idempotent"
        assert body["final_status"] in {"awaiting_approval", "completed"}
    await reset_engine()
    reset_settings_cache()


async def main() -> int:
    failures = 0
    for i in range(1, 6):
        try:
            await run_once(i)
            print(f"RUN {i}/5 PASS")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"RUN {i}/5 FAIL {type(exc).__name__}: {exc}")
    print("SUMMARY", "PASS" if failures == 0 else "FAIL", f"{5 - failures}/5")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
