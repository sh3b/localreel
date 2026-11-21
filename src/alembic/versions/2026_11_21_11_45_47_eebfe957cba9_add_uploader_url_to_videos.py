"""add uploader url to videos

Revision ID: eebfe957cba9
Revises: 8a8c09981200
Create Date: 2026-11-21 11:45:47.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "eebfe957cba9"
down_revision: str | Sequence[str] | None = "8a8c09981200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("videos", sa.Column("source_uploader_url", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("videos", "source_uploader_url")
