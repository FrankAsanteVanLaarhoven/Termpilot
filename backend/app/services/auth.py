"""Student passwords, hashed OTPs, httpOnly sessions. Never log secrets."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import timedelta
from typing import Any

from fastapi import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ids import new_id
from app.domain.models import AuthChallenge, AuthSession, RateLimitBucket, UserProfile
from app.services import clock
from app.services.formatter import hash_identifier
from app.settings import get_settings

ALGO = "pbkdf2_sha256"
ITERATIONS = 120_000
MIN_PASSWORD_LENGTH = 8
DEMO_PASSWORD = "termpilot"
SESSION_COOKIE = "tp_session"
OTP_TTL_MINUTES = 10
OTP_MAX_ATTEMPTS = 5
PHONE_RE = re.compile(r"^\+[1-9]\d{7,14}$")
GENERIC_LOGIN = "Email or password is incorrect."
GENERIC_CODE = "Invalid or expired code."
GENERIC_REGISTER = (
    "If that campus inbox is yours, we sent a 6-digit code. It expires in 10 minutes."
)
RATE_LIMITED = "Too many attempts. Try again in 15 minutes."


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), ITERATIONS
    ).hex()
    return f"{ALGO}${ITERATIONS}${salt}${digest}"


_DUMMY_PASSWORD_HASH: str | None = None


def dummy_password_hash() -> str:
    global _DUMMY_PASSWORD_HASH
    if _DUMMY_PASSWORD_HASH is None:
        _DUMMY_PASSWORD_HASH = hash_password("__timing_guard__")
    return _DUMMY_PASSWORD_HASH


def verify_password(password: str, stored: str | None) -> bool:
    if not password or not stored:
        return False
    parts = stored.split("$")
    if len(parts) != 4 or parts[0] != ALGO:
        return False
    _, iters, salt, digest = parts
    try:
        rounds = int(iters)
        check = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), rounds
        ).hex()
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(check, digest)


def password_error(password: str) -> str | None:
    if len(password) < MIN_PASSWORD_LENGTH:
        return (
            f"Choose a password of at least {MIN_PASSWORD_LENGTH} characters. "
            "First visit creates your account."
        )
    return None


def normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    compact = re.sub(r"[\s()-]", "", value.strip())
    if compact.startswith("00"):
        compact = "+" + compact[2:]
    if not PHONE_RE.match(compact):
        return None
    return compact


def mask_phone(value: str | None) -> str | None:
    if not value or len(value) < 6:
        return None
    return value[:3] + "••••" + value[-3:]


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(code: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{code}".encode()).hexdigest()


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def client_ip(request: Any) -> str:
    forwarded = ""
    if request is not None:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()[:80]
        if request.client:
            return (request.client.host or "local")[:80]
    return "local"


async def hit_rate_limit(
    session: AsyncSession,
    action: str,
    subject: str,
    *,
    limit: int,
    window_seconds: int = 900,
) -> bool:
    """Return True when the caller should be blocked. Subject is already a hash or IP.

    Uses a separate commit so a later HTTPException cannot roll the counter back.
    """
    del session
    from app.storage.database import get_session_factory

    now = clock.now()
    key = f"{action}:{subject}"[:120]
    factory = get_session_factory()
    async with factory() as extra:
        row = await extra.get(RateLimitBucket, key)
        blocked = False
        if row is None or (now - row.window_start).total_seconds() >= window_seconds:
            if row is None:
                extra.add(RateLimitBucket(id=key, window_start=now, count=1))
            else:
                row.window_start = now
                row.count = 1
        else:
            row.count += 1
            blocked = row.count > limit
        await extra.commit()
        return blocked


async def issue_otp(
    session: AsyncSession,
    *,
    user_id: str | None,
    dest: str,
    channel: str,
    purpose: str,
) -> str:
    from app.services.notify import deliver_otp

    code = generate_otp()
    salt = secrets.token_hex(16)
    now = clock.now()
    dest_hash = hash_identifier(dest)
    existing = (
        await session.execute(
            select(AuthChallenge).where(
                AuthChallenge.dest_hash == dest_hash,
                AuthChallenge.purpose == purpose,
                AuthChallenge.consumed_at.is_(None),
            )
        )
    ).scalars()
    for row in existing:
        row.consumed_at = now
    session.add(
        AuthChallenge(
            id=new_id("otp"),
            user_id=user_id,
            dest_hash=dest_hash,
            channel=channel,
            purpose=purpose,
            code_hash=f"{salt}${hash_otp(code, salt)}",
            expires_at=now + timedelta(minutes=OTP_TTL_MINUTES),
            created_at=now,
        )
    )
    await deliver_otp(dest, channel, code, purpose)
    return code


async def consume_otp(
    session: AsyncSession,
    *,
    dest: str,
    purpose: str,
    code: str,
) -> AuthChallenge | None:
    now = clock.now()
    dest_hash = hash_identifier(dest)
    rows = (
        (
            await session.execute(
                select(AuthChallenge)
                .where(
                    AuthChallenge.dest_hash == dest_hash,
                    AuthChallenge.purpose == purpose,
                    AuthChallenge.consumed_at.is_(None),
                )
                .order_by(AuthChallenge.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    if not rows:
        hash_otp(code or "000000", "deadbeef")
        return None
    row = rows[0]
    row.attempts += 1
    if now > row.expires_at or row.attempts > OTP_MAX_ATTEMPTS:
        row.consumed_at = now
        return None
    salt, stored = row.code_hash.split("$", 1)
    if not hmac.compare_digest(hash_otp(code.strip(), salt), stored):
        return None
    row.consumed_at = now
    return row


async def create_session(
    session: AsyncSession, user_id: str, request: Any | None = None
) -> str:
    raw = secrets.token_urlsafe(32)
    now = clock.now()
    days = get_settings().session_days
    session.add(
        AuthSession(
            id=new_id("sid"),
            user_id=user_id,
            token_hash=hash_session_token(raw),
            created_at=now,
            expires_at=now + timedelta(days=days),
            last_seen_at=now,
            ip_hash=hash_identifier(client_ip(request)),
        )
    )
    return raw


async def resolve_session(session: AsyncSession, token: str | None) -> str | None:
    if not token:
        return None
    now = clock.now()
    row = (
        await session.execute(
            select(AuthSession).where(AuthSession.token_hash == hash_session_token(token))
        )
    ).scalar_one_or_none()
    if row is None or row.revoked_at is not None or row.expires_at <= now:
        return None
    row.last_seen_at = now
    return row.user_id


async def revoke_session(session: AsyncSession, token: str | None) -> None:
    if not token:
        return
    row = (
        await session.execute(
            select(AuthSession).where(AuthSession.token_hash == hash_session_token(token))
        )
    ).scalar_one_or_none()
    if row is not None:
        row.revoked_at = clock.now()


def attach_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    secure = settings.env == "production" or settings.on_vercel
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=settings.session_days * 86400,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        httponly=True,
        secure=settings.env == "production" or settings.on_vercel,
        samesite="lax",
    )


def cache_guard(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"


async def get_user_by_email(session: AsyncSession, email: str) -> UserProfile | None:
    return (
        await session.execute(select(UserProfile).where(UserProfile.email == email))
    ).scalar_one_or_none()
