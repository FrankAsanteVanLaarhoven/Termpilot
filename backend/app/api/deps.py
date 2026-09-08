"""Request dependencies."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import UserProfile
from app.services.auth import SESSION_COOKIE, resolve_session
from app.services.identity import is_university_email, user_id_from_email
from app.settings import get_settings
from app.storage.database import get_session_factory, init_db


async def db_session() -> AsyncIterator[AsyncSession]:
    await init_db()
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def current_user_id(
    request: Request,
    session: AsyncSession = Depends(db_session),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_student_email: str | None = Header(default=None, alias="X-Student-Email"),
) -> str:
    settings = get_settings()
    cookie_user = await resolve_session(session, request.cookies.get(SESSION_COOKIE))
    if settings.strict_auth:
        if cookie_user:
            return cookie_user
        raise HTTPException(
            status_code=401,
            detail="Sign in with your campus account to use TermPilot.",
        )
    if x_user_id:
        uid = x_user_id
    elif cookie_user:
        return cookie_user
    else:
        uid = settings.demo_user_id
    user = await session.get(UserProfile, uid)
    if user is not None:
        return uid
    from app.services.demo import seed_user

    if x_student_email and is_university_email(x_student_email):
        expected = user_id_from_email(x_student_email)
        if expected == uid or not x_user_id:
            await seed_user(session, user_id=expected, email=x_student_email)
            return expected
    if uid == settings.demo_user_id:
        await seed_user(session, user_id=uid)
    return uid
