"""add source key to videos

Revision ID: ec4c911f3b50
Revises: fb4b45a1dc6d
Create Date: 2026-07-19 21:52:38.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ec4c911f3b50"
down_revision: str | Sequence[str] | None = "fb4b45a1dc6d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("videos", sa.Column("source_key", sa.Text(), nullable=False))
    op.create_unique_constraint("uq_videos_source_key", "videos", ["source_key"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_videos_source_key", "videos", type_="unique")
    op.drop_column("videos", "source_key")
