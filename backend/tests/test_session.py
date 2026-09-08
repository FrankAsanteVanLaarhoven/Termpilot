from __future__ import annotations

from httpx import AsyncClient


async def test_student_bootstrap_is_isolated(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    demo = await client.get("/me")
    assert demo.status_code == 200
    assert demo.json()["user_id"] == "FAVL"

    created = await client.post(
        "/session/bootstrap",
        json={"email": "alex.rivera@northbridge.ac.uk", "password": "rivera-lab-1"},
    )
    assert created.status_code == 200
    body = created.json()
    assert body["user_id"].startswith("stu_")
    assert body["email"] == "alex.rivera@northbridge.ac.uk"
    assert "Rivera" in body["display_name"]

    student_headers = {"X-User-Id": body["user_id"], "X-Student-Email": body["email"]}
    tower = await client.get("/tower", headers=student_headers)
    assert tower.status_code == 200
    workspace = await client.get("/workspace", headers=student_headers)
    assert workspace.status_code == 200
    connectors = {item["id"] for item in workspace.json()["connectors"]}
    assert "src_lms" in connectors
    assert "src_mailbox" in connectors
    assert "src_github" in connectors
    assert "src_jira" in connectors

    demo_again = await client.get("/me", headers={"X-User-Id": "FAVL"})
    assert demo_again.json()["user_id"] == "FAVL"


async def test_api_prefix_health(client: AsyncClient) -> None:
    response = await client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["student_login"] is True


async def test_student_password_required_and_checked(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    missing = await client.post(
        "/session/bootstrap", json={"email": "sam.lee@campus.ac.uk"}
    )
    assert missing.status_code == 400
    created = await client.post(
        "/session/bootstrap",
        json={"email": "sam.lee@campus.ac.uk", "password": "sam-secret"},
    )
    assert created.status_code == 200
    assert created.json()["created"] is True
    wrong = await client.post(
        "/session/bootstrap",
        json={"email": "sam.lee@campus.ac.uk", "password": "not-the-one"},
    )
    assert wrong.status_code == 401
    again = await client.post(
        "/session/bootstrap",
        json={"email": "sam.lee@campus.ac.uk", "password": "sam-secret"},
    )
    assert again.status_code == 200
    assert again.json()["created"] is False
    assert again.json()["user_id"] == created.json()["user_id"]


async def test_invalid_email_rejected(client: AsyncClient) -> None:
    response = await client.post("/session/bootstrap", json={"email": "not-an-email"})
    assert response.status_code == 400


async def test_newcastle_campus_email_can_bootstrap(client: AsyncClient) -> None:
    created = await client.post(
        "/session/bootstrap",
        json={
            "email": "F.Van-Laarhoven2@newcastle.ac.uk",
            "password": "campus-lab-1",
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert body["email"] == "f.van-laarhoven2@newcastle.ac.uk"
    assert body["user_id"].startswith("stu_")


async def test_personal_inbox_rejected_at_bootstrap(client: AsyncClient) -> None:
    gmail = await client.post(
        "/session/bootstrap",
        json={"email": "ada@gmail.com", "password": "not-campus"},
    )
    assert gmail.status_code == 400
    assert "university email" in gmail.json()["detail"].lower()
    random = await client.post(
        "/session/bootstrap",
        json={"email": "name@something.co.uk", "password": "not-campus"},
    )
    assert random.status_code == 400
    harvard = await client.post(
        "/session/bootstrap",
        json={"email": "ada@harvard.edu", "password": "campus-lab"},
    )
    assert harvard.status_code == 200
    tum = await client.post(
        "/session/bootstrap",
        json={"email": "lena@tum.de", "password": "campus-lab"},
    )
    assert tum.status_code == 200


async def test_public_demo_bootstrap_prepares_live_tower(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    created = await client.post(
        "/session/bootstrap",
        json={"email": "alex.rivera@northbridge.ac.uk", "password": "rivera-lab-1"},
    )
    assert created.status_code == 200
    body = created.json()
    assert body["prepared"]["connected"] >= 12
    assert body["prepared"]["obligations"] >= 1
    headers = {"X-User-Id": body["user_id"], "X-Student-Email": body["email"]}

    workspace = await client.get("/workspace", headers=headers)
    assert workspace.status_code == 200
    connectors = workspace.json()["connectors"]
    by_id = {item["id"]: item for item in connectors}
    assert all(item["connected"] for item in connectors)
    assert by_id["src_github"]["connected"] is True
    assert by_id["src_jira"]["connected"] is True
    assert by_id["src_linkedin"]["connected"] is True
    assert by_id["src_notion"]["connected"] is True
    assert by_id["src_slack"]["connected"] is True
    assert workspace.json()["notes"]

    tower = await client.get("/tower", headers=headers)
    assert tower.status_code == 200
    pack = tower.json()["tower"]
    assert pack["verified_obligations"] >= 1
    assert pack["open_conflicts"] >= 1

    mailbox = await client.get("/mailbox", headers=headers)
    assert mailbox.status_code == 200
    desk = mailbox.json()
    assert desk["authorised"] is True
    assert desk["student_email"] == "alex.rivera@northbridge.ac.uk"
    assert desk["counts"]["inbox"] >= 1
    assert desk["can_send"] is True

    feeds = await client.get("/feeds", headers=headers)
    assert feeds.status_code == 200
    assert feeds.json()["university_authorised"] is True

    asked = await client.post(
        "/grokbot/turn",
        headers=headers,
        json={"text": "what should I focus on this week?"},
    )
    assert asked.status_code == 200
    text = asked.json()["display_text"].lower()
    assert "verified" in text or "conflict" in text or "obligation" in text

    again = await client.post("/session/prepare", headers=headers)
    assert again.status_code == 200
    assert again.json()["reconciled"] is False
    assert again.json()["obligations"] >= 1

    demo = await client.get("/me", headers={"X-User-Id": "FAVL"})
    assert demo.json()["user_id"] == "FAVL"


async def test_two_students_can_share_fixture_notes(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    first = (
        await client.post(
            "/session/bootstrap", json={"email": "a.one@uni.ac.uk", "password": "student-one"}
        )
    ).json()
    second = (
        await client.post(
            "/session/bootstrap", json={"email": "b.two@uni.ac.uk", "password": "student-two"}
        )
    ).json()
    left = (
        await client.get(
            "/workspace",
            headers={"X-User-Id": first["user_id"], "X-Student-Email": first["email"]},
        )
    ).json()
    right = (
        await client.get(
            "/workspace",
            headers={"X-User-Id": second["user_id"], "X-Student-Email": second["email"]},
        )
    ).json()
    assert left["notes"]
    assert right["notes"]
    assert {note["id"] for note in left["notes"]} != {note["id"] for note in right["notes"]}


async def test_access_code_gate(client: AsyncClient) -> None:
    import os

    from app.settings import reset_settings_cache

    os.environ["TERMPILOT_ACCESS_CODE"] = "class-2026"
    reset_settings_cache()
    try:
        denied = await client.post(
            "/session/bootstrap",
            json={"email": "student@uni.ac.uk", "password": "student-lab"},
        )
        assert denied.status_code == 403
        allowed = await client.post(
            "/session/bootstrap",
            json={
                "email": "student@uni.ac.uk",
                "password": "student-lab",
                "access_code": "class-2026",
            },
        )
        assert allowed.status_code == 200
    finally:
        os.environ.pop("TERMPILOT_ACCESS_CODE", None)
        reset_settings_cache()
