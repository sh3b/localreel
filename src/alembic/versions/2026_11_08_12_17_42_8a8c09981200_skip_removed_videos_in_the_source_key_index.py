"""skip removed videos in the source key index

Revision ID: 8a8c09981200
Revises: 06859e909a94
Create Date: 2026-11-08 12:17:42.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8a8c09981200"
down_revision: str | Sequence[str] | None = "06859e909a94"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint("uq_videos_source_key", "videos", type_="unique")
    op.create_index(
        "uq_videos_source_key",
        "videos",
        ["source_key"],
        unique=True,
        postgresql_where=sa.text("status <> 'REMOVED'"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_videos_source_key", table_name="videos")
    op.create_unique_constraint("uq_videos_source_key", "videos", ["source_key"])
