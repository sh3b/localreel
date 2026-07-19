from psycopg.errors import UniqueViolation
from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from localreel.adapters.orm import VideoORM
from localreel.domain.exceptions import DuplicateVideo
from localreel.domain.models.video import Video
from localreel.domain.repository import AbstractVideoRepository


class PostgresVideoRepository(AbstractVideoRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def exists(self, *, source_key: str) -> bool:
        return bool(
            self._session.scalar(
                select(exists().where(VideoORM.source_key == source_key))
            )
        )

    def add(self, video: Video) -> None:
        self._session.add(
            VideoORM(
                id=video.id,
                source=video.source,
                source_url=video.source_url,
                source_key=video.source_key,
                status=video.status,
            )
        )
        try:
            self._session.flush()
        except IntegrityError as exc:
            violation = exc.orig
            if (
                isinstance(violation, UniqueViolation)
                and violation.diag.constraint_name == "uq_videos_source_key"
            ):
                raise DuplicateVideo(
                    f"A video with source key {video.source_key} exists"
                ) from exc
            raise
