"""add videos table

Revision ID: fb4b45a1dc6d
Revises:
Create Date: 2026-07-19 17:32:40.343718+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fb4b45a1dc6d"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "videos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("uploaded_by", sa.Uuid(), nullable=False),
        sa.Column(
            "source",
            sa.Enum("YOUTUBE", "TIKTOK", "FACEBOOK", "LOCAL", name="video_source"),
            nullable=False,
        ),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_url_hash", sa.String(length=64), nullable=True),
        sa.Column("file_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "visibility",
            sa.Enum("PRIVATE", "SHARED", name="video_visibility"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "DOWNLOADING",
                "DOWNLOADED",
                "TRANSCODING",
                "READY",
                "FAILED",
                name="video_status",
            ),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tags", sa.ARRAY(sa.Text()), nullable=False),
        sa.Column("duration_sec", sa.Integer(), nullable=True),
        sa.Column("hls_path", sa.Text(), nullable=True),
        sa.Column("thumbnail_path", sa.Text(), nullable=True),
        sa.Column("original_path", sa.Text(), nullable=True),
        sa.Column("phash", sa.String(length=64), nullable=True),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("view_count", sa.Integer(), nullable=False),
        sa.Column("source_file_available", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_url_hash"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("videos")
