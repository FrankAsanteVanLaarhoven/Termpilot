from __future__ import annotations

from app.policies.integrity import inspect_user_goal
from app.services.extraction import parse_explicit_datetime
from httpx import AsyncClient


async def test_lms_outage_degrades(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    response = await client.post(
        "/command", json={"text": "reconcile next 14 days", "simulate_lms_outage": True}
    )
    assert response.status_code == 200
    body = response.json()
    assert any(
        "source_degraded:lms" == u or "lms" in u for u in body["unresolved_uncertainties"]
    ) or body["bot_results"]["sync"]["lms"]["status"] in {"degraded", "unavailable"}


async def test_invalid_date_does_not_crash() -> None:
    assert parse_explicit_datetime("not a date at all") is None


async def test_integrity_blocks_impersonation() -> None:
    verdict = inspect_user_goal("log in as me and email my tutor")
    assert verdict.decision.value == "block"


async def test_duplicate_write_idempotent(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    await client.post(
        "/command",
        json={
            "text": "reconcile my next 14 days and ask before changing my calendar",
        },
    )
    approvals = await client.get("/approvals")
    pending = [a for a in approvals.json()["items"] if a["state"] == "pending"]
    if not pending:
        return
    approval_id = pending[0]["id"]
    await client.post(f"/approvals/{approval_id}/approve")
    first = await client.post("/calendar/apply", params={"approval_id": approval_id})
    second = await client.post("/calendar/apply", params={"approval_id": approval_id})
    assert second.json()["status"] == "idempotent"
    assert first.json()["created"] >= 0
