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
    assert first.json()["status"] == "check_email"
    assert "campus-lab" not in first.text.lower()
    assert first.json()["detail"]
    duplicate = await client.post(
        "/auth/register", json={"email": email, "password": "different-secret"}
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["detail"] == first.json()["detail"]
    assert "already" not in duplicate.json()["detail"].lower()


async def test_email_verify_sets_httponly_cookie_and_no_store(client: AsyncClient) -> None:
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


async def test_wrong_code_is_generic(client: AsyncClient) -> None:
    email = "lin@nus.edu.sg"
    await client.post("/auth/register", json={"email": email, "password": "campus-lab-1"})
    failed = await client.post(
        "/auth/verify-email", json={"email": email, "code": "000000"}
    )
    assert failed.status_code == 400
    assert "invalid or expired" in failed.json()["detail"].lower()
    assert "000000" not in failed.text


async def test_phone_2fa_enrolment(client: AsyncClient) -> None:
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
