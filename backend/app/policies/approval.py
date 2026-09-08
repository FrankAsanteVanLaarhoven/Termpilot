"""Approval expiry, replay protection and fail-closed writes."""

from __future__ import annotations

from app.domain.enums import ApprovalState
from app.domain.models import ApprovalRequest
from app.services import clock


class ApprovalError(PermissionError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def assert_usable(approval: ApprovalRequest, expected_target: str = "demo_calendar") -> None:
    now = clock.now()
    if approval.target_system != expected_target:
        raise ApprovalError("wrong_target", "Approval target does not match the demo calendar.")
    if approval.expires_at <= now and approval.state == ApprovalState.PENDING.value:
        approval.state = ApprovalState.EXPIRED.value
        raise ApprovalError("approval_expired", "This approval has expired. Request a new preview.")
    if approval.state == ApprovalState.EXPIRED.value:
        raise ApprovalError("approval_expired", "This approval has expired. Request a new preview.")
    if approval.state == ApprovalState.REJECTED.value:
        raise ApprovalError("approval_rejected", "This approval was rejected.")
    if approval.state not in {ApprovalState.APPROVED.value, ApprovalState.APPLIED.value}:
        raise ApprovalError("approval_not_granted", "Calendar writes require an approved request.")
