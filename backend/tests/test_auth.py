from __future__ import annotations

from app.services.notify import LAST_OTP
from app.settings import reset_settings_cache
from httpx import AsyncClient


async def test_register_hides_whether_the_account_exists(client: AsyncClient) -> None:
    email = "jo.k@newcastle.ac.uk"
    first = await client.post(
        "/auth/register", json={"email": email, "password": "campus-lab-1"}
    )
    assert first.status_code == 200
    assert first.json()["status"] == "ok"
    assert "campus-lab" not in first.text.lower()
    assert "tp_session=" in first.headers.get("set-cookie", "")
    duplicate = await client.post(
        "/auth/register", json={"email": email, "password": "different-secret"}
    )
    assert duplicate.status_code in {200, 401}
    assert "already" not in duplicate.text.lower()


async def test_email_verify_sets_httponly_cookie_and_no_store(
    client: AsyncClient, monkeypatch
) -> None:
    monkeypatch.setenv("TERMPILOT_REQUIRE_VERIFICATION", "true")
    reset_settings_cache()
    email = "ada.nguyen@ox.ac.uk"
    await client.post("/auth/register", json={"email": email, "password": "campus-lab-1"})
    code = LAST_OTP[f"email:{email}"]
    verified = await client.post(
        "/auth/verify-email", json={"email": email, "code": code}
    )
    assert verified.status_code == 200
    assert verified.json()["status"] == "ok"
    assert verified.json()["email_verified"] is True
    header = verified.headers.get("set-cookie", "")
    assert "tp_session=" in header
    assert "httponly" in header.lower()
    assert "samesite=lax" in header.lower()
    assert "no-store" in verified.headers.get("cache-control", "").lower()
    me = await client.get("/me")
    assert me.status_code == 200
    assert me.json()["email"] == email


async def test_wrong_code_is_generic(client: AsyncClient, monkeypatch) -> None:
    monkeypatch.setenv("TERMPILOT_REQUIRE_VERIFICATION", "true")
    reset_settings_cache()
    email = "lin@nus.edu.sg"
    await client.post("/auth/register", json={"email": email, "password": "campus-lab-1"})
    failed = await client.post(
        "/auth/verify-email", json={"email": email, "code": "000000"}
    )
    assert failed.status_code == 400
    assert "invalid or expired" in failed.json()["detail"].lower()
    assert "000000" not in failed.text


async def test_phone_2fa_enrolment(client: AsyncClient, monkeypatch) -> None:
    monkeypatch.setenv("TERMPILOT_REQUIRE_VERIFICATION", "true")
    reset_settings_cache()
    email = "hiro@u-tokyo.ac.jp"
    phone = "+447700900123"
    await client.post(
        "/auth/register",
        json={"email": email, "password": "campus-lab-1", "phone": phone},
    )
    email_code = LAST_OTP[f"email:{email}"]
    mid = await client.post(
        "/auth/verify-email",
        json={"email": email, "code": email_code, "phone": phone},
    )
    assert mid.status_code == 200
    assert mid.json()["status"] == "verify_phone"
    sms = LAST_OTP[f"sms:{phone}"]
    done = await client.post(
        "/auth/verify-phone",
        json={"email": email, "code": sms, "phone": phone},
    )
    assert done.status_code == 200
    assert done.json()["mfa_sms"] is True
    assert done.json()["phone_masked"] is not None
    assert phone not in (done.json()["phone_masked"] or "")


async def test_login_rate_limit(client: AsyncClient) -> None:
    last = None
    for _ in range(10):
        last = await client.post(
            "/auth/login", json={"email": "ada@gmail.com", "password": "not-campus"}
        )
    assert last is not None
    assert last.status_code == 429


async def test_production_login_requires_email_mfa(
    client: AsyncClient, monkeypatch
) -> None:
    monkeypatch.setenv("TERMPILOT_REQUIRE_VERIFICATION", "true")
    reset_settings_cache()
    email = "ciara@tcd.ie"
    await client.post("/auth/register", json={"email": email, "password": "campus-lab-1"})
    await client.post(
        "/auth/verify-email", json={"email": email, "code": LAST_OTP[f"email:{email}"]}
    )
    monkeypatch.setenv("TERMPILOT_ENV", "production")
    reset_settings_cache()
    try:
        challenge = await client.post(
            "/auth/login", json={"email": email, "password": "campus-lab-1"}
        )
        assert challenge.status_code == 200
        assert challenge.json()["status"] == "mfa_required"
        assert "tp_session=" not in challenge.headers.get("set-cookie", "")
        finished = await client.post(
            "/auth/mfa",
            json={
                "email": email,
                "channel": "email",
                "code": LAST_OTP[f"email:{email}"],
            },
        )
        assert finished.status_code == 200
        assert finished.json()["status"] == "ok"
        assert "tp_session=" in finished.headers.get("set-cookie", "")
    finally:
        monkeypatch.setenv("TERMPILOT_ENV", "test")
        reset_settings_cache()


async def test_demo_login_needs_no_email(client: AsyncClient) -> None:
    response = await client.post("/auth/demo")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["user_id"] == "FAVL"
    assert body["email"] == "demo@termpilot.org"
    assert body["display_name"] == "Demo student"
    assert "frankvanlaarhoven" not in response.text.lower()
    assert "tp_session=" in response.headers.get("set-cookie", "")


async def test_login_first_visit_creates_campus_account(client: AsyncClient) -> None:
    email = "new.student@bristol.ac.uk"
    response = await client.post(
        "/auth/login", json={"email": email, "password": "campus-lab-1"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["email"] == email
    assert body["user_id"].startswith("stu_")
    again = await client.post(
        "/auth/login", json={"email": email, "password": "campus-lab-1"}
    )
    assert again.status_code == 200
    assert again.json()["user_id"] == body["user_id"]
    wrong = await client.post(
        "/auth/login", json={"email": email, "password": "not-the-one"}
    )
    assert wrong.status_code == 401
    assert "incorrect" in wrong.json()["detail"].lower()


async def test_production_demo_login_without_register(
    client: AsyncClient, monkeypatch
) -> None:
    monkeypatch.setenv("TERMPILOT_ENV", "production")
    reset_settings_cache()
    try:
        response = await client.post("/auth/demo")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["user_id"] == "FAVL"
        assert response.json()["email"] == "demo@termpilot.org"
        assert "frankvanlaarhoven" not in response.text.lower()
        assert "tp_session=" in response.headers.get("set-cookie", "")
    finally:
        monkeypatch.setenv("TERMPILOT_ENV", "test")
        reset_settings_cache()


async def test_production_rejects_anonymous_and_spoofed_user(
    client: AsyncClient, monkeypatch
) -> None:
    monkeypatch.setenv("TERMPILOT_ENV", "production")
    reset_settings_cache()
    try:
        health = await client.get("/health")
        assert health.status_code == 200
        assert health.headers.get("x-frame-options") == "DENY"
        anon = await client.get("/tower")
        assert anon.status_code == 401
        assert "campus" in anon.json()["detail"].lower()
        spoof = await client.get("/tower", headers={"X-User-Id": "FAVL"})
        assert spoof.status_code == 401
        me = await client.get("/me")
        assert me.status_code == 401
    finally:
        monkeypatch.setenv("TERMPILOT_ENV", "test")
        reset_settings_cache()


async def test_production_session_cookie_opens_tower(
    client: AsyncClient, monkeypatch
) -> None:
    email = "member@ox.ac.uk"
    created = await client.post("/auth/register", json={"email": email, "password": "campus-lab-1"})
    assert created.status_code == 200
    assert "tp_session=" in created.headers.get("set-cookie", "")
    monkeypatch.setenv("TERMPILOT_ENV", "production")
    reset_settings_cache()
    try:
        tower = await client.get("/tower")
        assert tower.status_code == 200
        me = await client.get("/me", headers={"X-User-Id": "FAVL"})
        assert me.status_code == 200
        assert me.json()["email"] == email
    finally:
        monkeypatch.setenv("TERMPILOT_ENV", "test")
        reset_settings_cache()


async def test_signed_session_survives_a_fresh_database(
    client: AsyncClient, monkeypatch, tmp_path
) -> None:
    import os

    from app.storage.database import init_db, reset_engine

    demo = await client.post("/auth/demo")
    assert demo.status_code == 200
    token = demo.cookies.get("tp_session")
    assert token
    assert token.count("|") >= 4
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{tmp_path / 'fresh.db'}"
    monkeypatch.setenv("TERMPILOT_ENV", "production")
    reset_settings_cache()
    await reset_engine()
    await init_db()
    try:
        me = await client.get("/me")
        assert me.status_code == 200
        assert me.json()["user_id"] == "FAVL"
        tower = await client.get("/tower")
        assert tower.status_code == 200
    finally:
        monkeypatch.setenv("TERMPILOT_ENV", "test")
        reset_settings_cache()
        await reset_engine()
