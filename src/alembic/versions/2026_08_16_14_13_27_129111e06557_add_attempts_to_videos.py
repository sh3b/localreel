"""add attempts to videos

Revision ID: 129111e06557
Revises: f6de38c3c0f7
Create Date: 2026-08-16 14:13:27.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "129111e06557"
down_revision: str | Sequence[str] | None = "f6de38c3c0f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "videos",
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("videos", "attempts")
