"""add download_jobs table

Revision ID: eb14ab79e0c4
Revises: fb4b45a1dc6d
Create Date: 2026-07-21 22:17:36.492783+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "eb14ab79e0c4"
down_revision: str | Sequence[str] | None = "fb4b45a1dc6d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "download_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("video_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("download_jobs")
