from __future__ import annotations

from datetime import timedelta

import pytest
from app.domain.enums import ApprovalState
from app.domain.models import ApprovalRequest
from app.policies.approval import ApprovalError, assert_usable
from app.services.clock import now


def _approval(state: str, minutes: int = 30) -> ApprovalRequest:
    current = now()
    return ApprovalRequest(
        id="apr_test",
        user_id="FAVL",
        action_type="calendar_write",
        target_system="demo_calendar",
        reason="test",
        diff_json={},
        state=state,
        idempotency_key="k1",
        reversible=True,
        expires_at=current + timedelta(minutes=minutes),
        created_at=current,
    )


def test_pending_approval_is_not_usable() -> None:
    with pytest.raises(ApprovalError):
        assert_usable(_approval(ApprovalState.PENDING.value))


def test_expired_approval_fails_closed() -> None:
    row = _approval(ApprovalState.PENDING.value, minutes=-1)
    with pytest.raises(ApprovalError) as exc:
        assert_usable(row)
    assert exc.value.code == "approval_expired"


def test_approved_can_write() -> None:
    assert_usable(_approval(ApprovalState.APPROVED.value))
