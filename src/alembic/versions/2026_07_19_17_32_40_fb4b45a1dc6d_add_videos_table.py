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
        sa.Column(
            "source",
            sa.Enum(
                "YOUTUBE",
                "TIKTOK",
                "FACEBOOK",
                name="video_source",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", name="video_status", native_enum=False, length=32),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("videos")
