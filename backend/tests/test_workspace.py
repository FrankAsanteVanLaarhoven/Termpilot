from __future__ import annotations

from httpx import AsyncClient


async def test_optional_connectors_start_disconnected(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    workspace = (await client.get("/workspace")).json()
    linkedin = next(c for c in workspace["connectors"] if c["id"] == "src_linkedin")
    assert linkedin["connected"] is False
    assert linkedin["oauth"] == "fixture-adapter"
    assert linkedin["one_click"] is True
    assert linkedin["production_url"]
    assert workspace["live"] is True
    assert workspace["meetings"]
    lms = next(c for c in workspace["connectors"] if c["id"] == "src_lms")
    assert lms["connected"] is True
    assert lms["last_success_at"]


async def test_student_connect_all_uses_namespaced_connection_ids(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    created = (
        await client.post(
            "/session/bootstrap",
            json={"email": "casey.nguyen@campus.ac.uk", "password": "casey-lab-1"},
        )
    ).json()
    headers = {"X-User-Id": created["user_id"], "X-Student-Email": created["email"]}
    linked = await client.post("/connectors/connect-all", headers=headers, json={})
    assert linked.status_code == 200
    assert linked.json()["count"] >= 6
    workspace = (await client.get("/workspace", headers=headers)).json()
    assert all(item["connected"] for item in workspace["connectors"])
    assert any(note["source"] == "notion" for note in workspace["notes"])


async def test_connect_all_is_one_click(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    result = (await client.post("/connectors/connect-all", json={})).json()
    assert result["one_click"] is True
    assert result["count"] >= 12
    workspace = (await client.get("/workspace")).json()
    ids = {c["id"] for c in workspace["connectors"]}
    assert {
        "src_github",
        "src_jira",
        "src_linkedin",
        "src_notion",
        "src_slack",
        "src_mailbox",
        "src_teams",
        "src_discord",
        "src_gdrive",
    } <= ids
    assert all(c["connected"] for c in workspace["connectors"])
    start = (await client.get("/connectors/src_github/oauth/start")).json()
    assert start["one_click"] is True
    assert start["oauth_ready"] is False
    assert "github" in (start["docs_url"] or start["production_url"] or "")


async def test_one_click_github_and_jira_need_no_oauth_keys(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    github = await client.post("/connectors/src_github/connect")
    jira = await client.post("/connectors/src_jira/connect")
    assert github.status_code == 200
    assert jira.status_code == 200
    assert github.json()["one_click"] is True
    assert github.json()["connected"] is True
    assert github.json()["oauth_ready"] is False
    workspace = (await client.get("/workspace")).json()
    by_id = {c["id"]: c for c in workspace["connectors"]}
    assert by_id["src_github"]["connected"] is True
    assert by_id["src_jira"]["connected"] is True


async def test_connect_notion_and_organise_notes(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    connected = await client.post("/connectors/src_notion/connect")
    assert connected.status_code == 200
    organised = await client.post("/workspace/notes/organise")
    assert organised.status_code == 200
    assert organised.json()["organised"] >= 1


async def test_email_draft_requires_mailbox_and_approval(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    blocked = await client.post(
        "/workspace/messages/draft",
        json={"to_address": "tutor@example.edu", "subject": "Hi", "body": "Draft only"},
    )
    assert blocked.status_code == 403
    await client.post("/connectors/src_mailbox/connect")
    drafted = await client.post(
        "/workspace/messages/draft",
        json={"to_address": "tutor@example.edu", "subject": "Hi", "body": "Draft only"},
    )
    assert drafted.status_code == 200
    body = drafted.json()
    assert body["sent"] is False
    send_blocked = await client.post(f"/workspace/messages/{body['message_id']}/send")
    assert send_blocked.status_code == 409
    await client.post(f"/approvals/{body['approval_id']}/approve")
    sent = await client.post(f"/workspace/messages/{body['message_id']}/send")
    assert sent.status_code == 200
    assert sent.json()["status"] == "sent_demo_outbox"
    replay = await client.post(f"/workspace/messages/{body['message_id']}/send")
    assert replay.json()["status"] == "idempotent"
