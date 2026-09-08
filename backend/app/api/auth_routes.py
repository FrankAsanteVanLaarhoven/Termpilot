"""Register, verify, login, 2FA. Responses never reveal whether an account exists."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.domain.models import UserProfile
from app.services import clock
from app.services.auth import (
    GENERIC_CODE,
    GENERIC_LOGIN,
    GENERIC_REGISTER,
    RATE_LIMITED,
    SESSION_COOKIE,
    attach_session_cookie,
    cache_guard,
    clear_session_cookie,
    client_ip,
    consume_otp,
    create_session,
    dummy_password_hash,
    get_user_by_email,
    hit_rate_limit,
    issue_otp,
    mask_phone,
    normalize_phone,
    password_error,
    revoke_session,
    verify_password,
)
from app.services.collaborate import me as current_profile
from app.services.demo import prepare_student_workspace, seed_user
from app.services.formatter import hash_identifier
from app.services.identity import (
    display_name_from_email,
    is_demo_email,
    university_email_error,
    user_id_from_email,
)
from app.settings import get_settings

router = APIRouter(tags=["auth"])


class RegisterIn(BaseModel):
    email: str
    password: str
    phone: str | None = None
    access_code: str | None = None


class LoginIn(BaseModel):
    email: str
    password: str
    access_code: str | None = None


class VerifyIn(BaseModel):
    email: str
    code: str
    phone: str | None = None


class MfaIn(BaseModel):
    email: str
    channel: str = "email"
    code: str | None = None
    phone: str | None = None


def _guard(response: Response) -> None:
    cache_guard(response)


def _can_email_otp() -> bool:
    settings = get_settings()
    return bool(settings.resend_api_key) or settings.env == "test" or bool(
        os.environ.get("PYTEST_CURRENT_TEST")
    )


async def _blocked(session: AsyncSession, action: str, request: Request, email: str) -> None:
    ip = hash_identifier(client_ip(request))
    mail = hash_identifier(email)
    if await hit_rate_limit(session, action, ip, limit=8) or await hit_rate_limit(
        session, action, mail, limit=8
    ):
        raise HTTPException(status_code=429, detail=RATE_LIMITED)


async def _finish_login(
    session: AsyncSession,
    request: Request,
    response: Response,
    user_id: str,
) -> dict[str, Any]:
    token = await create_session(session, user_id, request)
    attach_session_cookie(response, token)
    try:
        prepared = await prepare_student_workspace(session, user_id)
    except Exception:  # noqa: BLE001
        prepared = {"connected": 0, "reconciled": False, "obligations": 0, "public_demo": True}
    profile = await current_profile(session, user_id)
    user = await session.get(UserProfile, user_id)
    return {
        "status": "ok",
        "created": False,
        **profile,
        "email_verified": bool(user and user.email_verified_at),
        "phone_masked": mask_phone(user.phone_e164 if user else None),
        "mfa_sms": bool(user and user.mfa_sms_enabled),
        "prepared": prepared,
    }


@router.post("/auth/register")
async def register(
    body: RegisterIn,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    _guard(response)
    email = body.email.strip().lower()
    await _blocked(session, "register", request, email)
    if university_email_error(email):
        raise HTTPException(
            status_code=400,
            detail="Use a real university email from your campus. Personal inboxes are not accepted.",
        )
    problem = password_error(body.password)
    if problem:
        raise HTTPException(status_code=400, detail=problem)
    settings = get_settings()
    if settings.access_code and not is_demo_email(email):
        if (body.access_code or "") != settings.access_code:
            raise HTTPException(status_code=403, detail="Enter the classroom access code.")
    phone = normalize_phone(body.phone)
    if body.phone and not phone:
        raise HTTPException(status_code=400, detail="Use an international phone number like +447700900123.")
    existing = await get_user_by_email(session, email)
    if existing is None:
        seeded = await seed_user(
            session,
            user_id=user_id_from_email(email),
            display_name=display_name_from_email(email),
            email=email,
            password=body.password,
            email_verified=is_demo_email(email),
        )
        user = await session.get(UserProfile, seeded["user_id"])
        if user is not None and phone:
            user.phone_e164 = phone
    elif existing.password_hash and not verify_password(body.password, existing.password_hash):
        if not existing.email_verified_at and not _can_email_otp():
            from app.services.auth import hash_password

            existing.password_hash = hash_password(body.password)
            existing.updated_at = clock.now()
        else:
            verify_password(body.password, dummy_password_hash())
            return {"status": "check_email", "detail": GENERIC_REGISTER}
    if is_demo_email(email):
        return await _finish_login(session, request, response, user_id_from_email(email))
    if _can_email_otp():
        await issue_otp(session, user_id=user_id_from_email(email), dest=email, channel="email", purpose="signup")
        return {"status": "check_email", "detail": GENERIC_REGISTER}
    user = existing or await get_user_by_email(session, email)
    if user is None:
        return {"status": "check_email", "detail": GENERIC_REGISTER}
    return await _finish_login(session, request, response, user.id)


@router.post("/auth/verify-email")
async def verify_email(
    body: VerifyIn,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    _guard(response)
    email = body.email.strip().lower()
    await _blocked(session, "verify", request, email)
    user = await get_user_by_email(session, email)
    challenge = await consume_otp(session, dest=email, purpose="signup", code=body.code)
    if user is None or challenge is None:
        raise HTTPException(status_code=400, detail=GENERIC_CODE)
    user.email_verified_at = clock.now()
    user.updated_at = clock.now()
    phone = normalize_phone(body.phone) or user.phone_e164
    if phone:
        user.phone_e164 = phone
        await issue_otp(session, user_id=user.id, dest=phone, channel="sms", purpose="phone")
        return {
            "status": "verify_phone",
            "detail": "Email confirmed. Enter the code sent to your mobile to turn on SMS 2FA.",
            "phone_masked": mask_phone(phone),
        }
    return await _finish_login(session, request, response, user.id)


@router.post("/auth/verify-phone")
async def verify_phone(
    body: VerifyIn,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    _guard(response)
    email = body.email.strip().lower()
    await _blocked(session, "verify", request, email)
    user = await get_user_by_email(session, email)
    phone = normalize_phone(body.phone) or (user.phone_e164 if user else None)
    if user is None or not phone or not user.email_verified_at:
        raise HTTPException(status_code=400, detail=GENERIC_CODE)
    challenge = await consume_otp(session, dest=phone, purpose="phone", code=body.code)
    if challenge is None:
        raise HTTPException(status_code=400, detail=GENERIC_CODE)
    user.phone_verified_at = clock.now()
    user.mfa_sms_enabled = True
    user.updated_at = clock.now()
    return await _finish_login(session, request, response, user.id)


@router.post("/auth/login")
async def login(
    body: LoginIn,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    _guard(response)
    email = body.email.strip().lower()
    await _blocked(session, "login", request, email)
    if university_email_error(email) and not is_demo_email(email):
        verify_password(body.password or "xxxxxxxx", dummy_password_hash())
        raise HTTPException(status_code=401, detail=GENERIC_LOGIN)
    settings = get_settings()
    if settings.access_code and not is_demo_email(email):
        if (body.access_code or "") != settings.access_code:
            raise HTTPException(status_code=403, detail="Enter the classroom access code.")
    user = await get_user_by_email(session, email)
    stored = user.password_hash if user else dummy_password_hash()
    allowed = verify_password(body.password, stored)
    if user is None or not allowed:
        raise HTTPException(status_code=401, detail=GENERIC_LOGIN)
    if is_demo_email(email) or not settings.strict_auth:
        return await _finish_login(session, request, response, user.id)
    if not user.email_verified_at:
        if not _can_email_otp():
            return await _finish_login(session, request, response, user.id)
        await issue_otp(session, user_id=user.id, dest=email, channel="email", purpose="signup")
        return {"status": "verify_email", "detail": GENERIC_REGISTER}
    if not _can_email_otp() and not (user.mfa_sms_enabled and user.phone_e164):
        return await _finish_login(session, request, response, user.id)
    channel = "sms" if user.mfa_sms_enabled and user.phone_e164 else "email"
    dest = user.phone_e164 if channel == "sms" else email
    await issue_otp(session, user_id=user.id, dest=dest, channel=channel, purpose="login_mfa")
    return {
        "status": "mfa_required",
        "channel": channel,
        "phone_masked": mask_phone(user.phone_e164),
        "detail": "Enter the 6-digit code we sent to finish signing in.",
    }


@router.post("/auth/mfa")
async def mfa(
    body: MfaIn,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    _guard(response)
    email = body.email.strip().lower()
    await _blocked(session, "mfa", request, email)
    user = await get_user_by_email(session, email)
    if user is None or not user.email_verified_at:
        raise HTTPException(status_code=401, detail=GENERIC_LOGIN)
    channel = body.channel if body.channel in {"email", "sms"} else "email"
    if channel == "sms" and not (user.mfa_sms_enabled and user.phone_e164):
        channel = "email"
    dest = user.phone_e164 if channel == "sms" else email
    if not body.code:
        await issue_otp(session, user_id=user.id, dest=dest, channel=channel, purpose="login_mfa")
        return {
            "status": "mfa_required",
            "channel": channel,
            "phone_masked": mask_phone(user.phone_e164),
            "detail": "Enter the 6-digit code we sent to finish signing in.",
        }
    challenge = await consume_otp(session, dest=dest, purpose="login_mfa", code=body.code)
    if challenge is None:
        raise HTTPException(status_code=400, detail=GENERIC_CODE)
    return await _finish_login(session, request, response, user.id)


@router.post("/auth/logout")
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(db_session),
) -> dict[str, str]:
    _guard(response)
    await revoke_session(session, request.cookies.get(SESSION_COOKIE))
    clear_session_cookie(response)
    return {"status": "signed_out"}
