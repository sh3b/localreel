"""rename videos.hls_path to playback_path

Revision ID: 4fce4c2898e7
Revises: eb14ab79e0c4
Create Date: 2026-08-10 20:40:48.716366+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4fce4c2898e7"
down_revision: str | Sequence[str] | None = "eb14ab79e0c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column("videos", "hls_path", new_column_name="playback_path")


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("videos", "playback_path", new_column_name="hls_path")
