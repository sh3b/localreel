from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from localreel.adapters import orm
from localreel.domain.abstractions.repository import AbstractVideoRepository
from localreel.domain.exceptions import VideoNotFound
from localreel.domain.models.video import Video
from localreel.domain.types import VideoSource, VideoStatus


class PostgresVideoRepository(AbstractVideoRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, video: Video) -> None:
        self._session.add(video)

    def get(self, video_id: UUID) -> Video:
        # Locked: every caller changes the video, and two writers (a worker's
        # heartbeat or outcome, a sweep) must not both act on a status that one
        # of them is about to change.
        video = self._session.get(Video, video_id, with_for_update=True)
        if video is None:
            raise VideoNotFound(f"Video {video_id} not found")
        return video

    def get_by_source_url_hash(self, source_url_hash: str) -> Video | None:
        stmt = select(Video).where(orm.videos.c.source_url_hash == source_url_hash)
        return self._session.scalars(stmt).first()

    def get_next_pending(self) -> Video | None:
        # LOCAL uploads go PENDING -> DOWNLOADED with no download step, so the
        # worker must never claim them. FOR UPDATE SKIP LOCKED lets several
        # workers compete for rows without a separate queue table.
        stmt = (
            select(Video)
            .where(orm.videos.c.status == VideoStatus.PENDING)
            .where(orm.videos.c.source != VideoSource.LOCAL)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def get_next_downloaded(self) -> Video | None:
        # No source filter, unlike get_next_pending: LOCAL uploads reach
        # DOWNLOADED too and need the same normalize-and-thumbnail pass.
        stmt = (
            select(Video)
            .where(orm.videos.c.status == VideoStatus.DOWNLOADED)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def get_stalled(self, status: VideoStatus, beat_before: datetime) -> list[Video]:
        # SKIP LOCKED: a row its worker is persisting right now is not stalled,
        # and two sweeps never fail the same row.
        stmt = (
            select(Video)
            .where(orm.videos.c.status == status)
            .where(orm.videos.c.heartbeat_at < beat_before)
            .with_for_update(skip_locked=True)
        )
        return list(self._session.scalars(stmt))
