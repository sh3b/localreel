"""add download result to videos

Revision ID: 54940bd11696
Revises: ec4c911f3b50
Create Date: 2026-08-09 20:23:34.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "54940bd11696"
down_revision: str | Sequence[str] | None = "ec4c911f3b50"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("videos", sa.Column("file_path", sa.Text(), nullable=True))
    op.add_column("videos", sa.Column("error", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("videos", "error")
    op.drop_column("videos", "file_path")
