from __future__ import annotations

from app.services.mailbox import HIERARCHY, STUDENT_EMAIL
from app.services.voicebridge import classify_intent
from httpx import AsyncClient


def test_mail_intents() -> None:
    assert classify_intent("clean my inbox") == "mailbox_cleanup"
    assert classify_intent("mail alerts") == "mailbox_alerts"
    assert classify_intent("draft an email") == "mailbox_draft"
    assert classify_intent("check email") == "email"


async def test_me_includes_student_email(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    me = (await client.get("/me")).json()
    assert me["email"] == STUDENT_EMAIL
    assert me["username"] == "FAVL"


async def test_mailbox_desk_priority_hierarchy(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    body = (await client.get("/mailbox")).json()
    assert body["smtp"] is False
    assert body["student_email"] == STUDENT_EMAIL
    assert [step["fn"] for step in body["hierarchy"]] == [step["fn"] for step in HIERARCHY]
    assert body["counts"]["p0"] >= 1
    assert body["counts"]["p3"] >= 1
    assert all(item["priority"] == "p0" for item in body["alerts"])
    inbox_ids = {item["id"] for item in body["items"] if item["state"] == "inbox"}
    assert "mail_cas" in inbox_ids
    assert "mail_promo_laptops" in inbox_ids


async def test_cleanup_archives_clutter_keeps_deadlines(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    cleaned = (await client.post("/mailbox/cleanup")).json()
    assert cleaned["smtp"] is False
    assert cleaned["counts"]["archived_now"] >= 1
    assert "mail_cas" in cleaned["kept"]
    assert "mail_deadline" in cleaned["kept"]
    assert "mail_promo_laptops" in cleaned["archived"]
    desk = (await client.get("/mailbox")).json()
    states = {item["id"]: item["state"] for item in desk["items"]}
    assert states["mail_cas"] == "inbox"
    assert states["mail_promo_laptops"] == "archived"
    assert desk["counts"]["p0"] >= 1
    assert desk["counts"]["p3"] == 0


async def test_draft_requires_student_mailbox_and_approval(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    blocked = await client.post("/mailbox/mail_deadline/draft")
    assert blocked.status_code == 403
    await client.post("/connectors/src_mailbox/connect")
    drafted = await client.post("/mailbox/mail_deadline/draft")
    assert drafted.status_code == 200
    body = drafted.json()
    assert body["sent"] is False
    send = await client.post(f"/workspace/messages/{body['message_id']}/send")
    assert send.status_code == 409
    await client.post(f"/approvals/{body['approval_id']}/approve")
    sent = await client.post(f"/workspace/messages/{body['message_id']}/send")
    assert sent.json()["status"] == "sent_demo_outbox"


async def test_voice_cleanup_opens_mailbox(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    body = (
        await client.post(
            "/voicebridge/turn",
            json={"text": "clean my inbox", "language": "en"},
        )
    ).json()
    assert body["facts"]["open_view"] == "mailbox"
    assert body["facts"]["counts"]["archived_now"] >= 1
