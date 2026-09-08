"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-05
"""

from __future__ import annotations

from typing import Sequence, Union

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Demo uses SQLAlchemy create_all. This revision documents the baseline.
    pass


def downgrade() -> None:
    pass
