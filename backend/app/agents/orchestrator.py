"""Orchestrator bot: delegate bounded work, never bypass Guardian or Verifier."""

from app.services.pipeline import reconcile

__all__ = ["reconcile"]
