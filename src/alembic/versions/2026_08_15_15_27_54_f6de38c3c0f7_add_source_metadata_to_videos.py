"""add source metadata to videos

Revision ID: f6de38c3c0f7
Revises: 54940bd11696
Create Date: 2026-08-15 15:27:54.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6de38c3c0f7"
down_revision: str | Sequence[str] | None = "54940bd11696"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("videos", sa.Column("thumbnail_path", sa.Text(), nullable=True))
    op.add_column("videos", sa.Column("source_title", sa.Text(), nullable=True))
    op.add_column("videos", sa.Column("source_description", sa.Text(), nullable=True))
    op.add_column("videos", sa.Column("source_uploader", sa.Text(), nullable=True))
    op.add_column(
        "videos", sa.Column("source_view_count", sa.BigInteger(), nullable=True)
    )
    op.add_column(
        "videos", sa.Column("source_duration_sec", sa.Integer(), nullable=True)
    )
    op.add_column(
        "videos",
        sa.Column("source_raw", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("videos", "source_raw")
    op.drop_column("videos", "source_duration_sec")
    op.drop_column("videos", "source_view_count")
    op.drop_column("videos", "source_uploader")
    op.drop_column("videos", "source_description")
    op.drop_column("videos", "source_title")
    op.drop_column("videos", "thumbnail_path")
