"""add size to videos

Revision ID: 06859e909a94
Revises: 3c7e9a1f5b2d
Create Date: 2026-11-01 22:21:37.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "06859e909a94"
down_revision: str | Sequence[str] | None = "3c7e9a1f5b2d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("videos", sa.Column("source_width", sa.Integer(), nullable=True))
    op.add_column("videos", sa.Column("source_height", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("videos", "source_height")
    op.drop_column("videos", "source_width")
