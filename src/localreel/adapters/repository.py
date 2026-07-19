from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from localreel.adapters import orm
from localreel.domain.abstractions.repository import AbstractVideoRepository
from localreel.domain.exceptions import VideoNotFound
from localreel.domain.models.video import Video


class PostgresVideoRepository(AbstractVideoRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, video: Video) -> None:
        self._session.add(video)

    def get(self, video_id: UUID) -> Video:
        video = self._session.get(Video, video_id)
        if video is None:
            raise VideoNotFound(f"Video {video_id} not found")
        return video

    def get_by_source_url_hash(self, source_url_hash: str) -> Video | None:
        stmt = select(Video).where(orm.videos.c.source_url_hash == source_url_hash)
        return self._session.scalars(stmt).first()
