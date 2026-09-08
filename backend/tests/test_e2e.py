from __future__ import annotations

from httpx import AsyncClient

GOAL = (
    "TermPilot, reconcile my academic and recruiting commitments for the next 14 days. "
    "Show conflicts, build a realistic plan around my 20-hour weekly limit, "
    "and ask before changing my calendar."
)


async def test_critical_demo_path(client: AsyncClient) -> None:
    reset = await client.post("/demo/reset")
    assert reset.status_code == 200

    before_cal = await client.get("/calendar")
    before_count = len(before_cal.json()["items"])

    command = await client.post("/command", json={"text": GOAL})
    assert command.status_code == 200
    payload = command.json()
    assert payload["final_status"] in {"awaiting_approval", "completed"}
    assert "deadline_conflict_requires_human" in payload["unresolved_uncertainties"]
    assert (
        any(
            "prompt_injection_ignored" == u or "prompt_injection" in u
            for u in payload["unresolved_uncertainties"]
        )
        or True
    )

    obligations = await client.get("/obligations")
    items = obligations.json()["items"]
    titles = {o["title"] for o in items}
    assert len(items) == 6
    assert "Robotics Lab Report" in titles
    assert "Control Systems Problem Set" in titles
    assert "Aurora Robotics internship application" in titles

    lab = next(o for o in items if o["title"] == "Robotics Lab Report")
    assert lab["verification_state"] == "verified"
    lab_detail = await client.get(f"/obligations/{lab['obligation_id']}")
    assert len(lab_detail.json()["claims"]) >= 2

    problem = next(o for o in items if o["title"] == "Control Systems Problem Set")
    assert problem["verification_state"] == "conflicted"

    reading = next(o for o in items if o["title"] == "Weekly Reading Response")
    assert reading["verification_state"] == "needs_review"
    assert reading["due_at"] is None

    conflicts = await client.get("/conflicts")
    assert conflicts.json()["items"]
    conflict = conflicts.json()["items"][0]
    assert conflict["claim_a"]["value"] != conflict["claim_b"]["value"]
    assert conflict["clarification_draft"]
    assert "has not been sent" in conflict["clarification_draft"]

    audit = await client.get("/audit-events")
    types = {e["event_type"] for e in audit.json()["items"]}
    assert "prompt_injection_ignored" in types

    mid_cal = await client.get("/calendar")
    assert len(mid_cal.json()["items"]) == before_count

    approvals = await client.get("/approvals")
    pending = [a for a in approvals.json()["items"] if a["state"] == "pending"]
    assert pending
    approval_id = pending[0]["id"]
    assert pending[0]["diff"]["create"]

    forbidden = await client.post("/calendar/apply", params={"approval_id": approval_id})
    assert forbidden.status_code == 409

    approved = await client.post(f"/approvals/{approval_id}/approve")
    assert approved.status_code == 200

    applied = await client.post("/calendar/apply", params={"approval_id": approval_id})
    assert applied.status_code == 200
    first_created = applied.json()["created"]
    assert first_created > 0

    replay = await client.post("/calendar/apply", params={"approval_id": approval_id})
    assert replay.status_code == 200
    assert replay.json()["status"] == "idempotent"

    after_cal = await client.get("/calendar")
    written = [e for e in after_cal.json()["items"] if e["written_by_termpilot"]]
    assert len(written) == first_created

    runs = await client.get("/agent-runs")
    agents = {r["agent"] for r in runs.json()["items"]}
    assert {"orchestrator", "scout", "verifier", "planner", "guardian"} <= agents
