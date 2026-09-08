from __future__ import annotations

import pytest
from app.domain.enums import ConsentPurpose
from app.policies.consent import ConsentError, require_consent
from app.services.demo import seed_user
from app.storage.database import get_session_factory, init_db


async def test_consent_required(client) -> None:  # type: ignore[no-untyped-def]
    del client
    await init_db()
    factory = get_session_factory()
    async with factory() as session:
        await seed_user(session)
        await session.commit()
        grant = await require_consent(session, "FAVL", ConsentPurpose.SOURCE_READ, "lms")
        assert grant.granted is True
        with pytest.raises(ConsentError):
            await require_consent(session, "usr_unknown", ConsentPurpose.CALENDAR_WRITE)
