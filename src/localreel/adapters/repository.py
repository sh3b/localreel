from uuid import UUID

from psycopg.errors import UniqueViolation
from sqlalchemy import delete, exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from localreel.adapters.orm import VideoORM
from localreel.domain.exceptions import DuplicateVideo, VideoNotFound
from localreel.domain.models.video import Video
from localreel.domain.repository import AbstractVideoRepository
from localreel.domain.value_objects import SourceMetadata, VideoStatus


class PostgresVideoRepository(AbstractVideoRepository):
    def __init__(self, session: Session) -> None:
        self._session = session
        self.seen: dict[UUID, Video] = {}

    def exists(self, *, source_key: str) -> bool:
        return bool(
            self._session.scalar(
                select(
                    exists().where(
                        VideoORM.source_key == source_key,
                        VideoORM.status != VideoStatus.REMOVED,
                    )
                )
            )
        )

    def add(self, video: Video) -> None:
        self._session.add(self._to_orm(video))
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
        self.seen[video.id] = video

    def get(self, video_id: UUID, *, lock: bool) -> Video:
        row = self._session.get(VideoORM, video_id, with_for_update=lock)
        if row is None:
            raise VideoNotFound(f"Video {video_id} not found")
        # A second get must hand back the same object: a fresh copy would
        # replace the changed one, and the commit would save the stale state.
        if video_id not in self.seen:
            self.seen[video_id] = self._to_domain(row)
        return self.seen[video_id]

    def next_pending(self) -> UUID | None:
        return self._session.scalars(
            select(VideoORM.id)
            .where(VideoORM.status == VideoStatus.PENDING)
            .order_by(VideoORM.id)
            .limit(1)
        ).first()

    def downloading(self) -> list[UUID]:
        return list(
            self._session.scalars(
                select(VideoORM.id).where(VideoORM.status == VideoStatus.DOWNLOADING)
            )
        )

    def failed(self) -> list[UUID]:
        return list(
            self._session.scalars(
                select(VideoORM.id).where(VideoORM.status == VideoStatus.FAILED)
            )
        )

    def removed(self) -> list[UUID]:
        return list(
            self._session.scalars(
                select(VideoORM.id).where(VideoORM.status == VideoStatus.REMOVED)
            )
        )

    def save(self, video: Video) -> None:
        self._session.merge(self._to_orm(video))

    def delete(self, video: Video) -> None:
        self._session.execute(delete(VideoORM).where(VideoORM.id == video.id))

    @staticmethod
    def _to_domain(row: VideoORM) -> Video:
        source_metadata = None
        if row.source_raw is not None:
            source_metadata = SourceMetadata(
                title=row.source_title,
                description=row.source_description,
                uploader=row.source_uploader,
                uploader_url=row.source_uploader_url,
                view_count=row.source_view_count,
                duration_sec=row.source_duration_sec,
                width=row.source_width,
                height=row.source_height,
                raw=row.source_raw,
            )

        return Video(
            id=row.id,
            source=row.source,
            source_url=row.source_url,
            source_key=row.source_key,
            status=row.status,
            attempts=row.attempts,
            file_path=row.file_path,
            thumbnail_path=row.thumbnail_path,
            source_metadata=source_metadata,
            error=row.error,
        )

    @staticmethod
    def _to_orm(video: Video) -> VideoORM:
        row = VideoORM(
            id=video.id,
            source=video.source,
            source_url=video.source_url,
            source_key=video.source_key,
            status=video.status,
            attempts=video.attempts,
            file_path=video.file_path,
            thumbnail_path=video.thumbnail_path,
            error=video.error,
        )

        metadata = video.source_metadata
        if metadata is not None:
            row.source_title = metadata.title
            row.source_description = metadata.description
            row.source_uploader = metadata.uploader
            row.source_uploader_url = metadata.uploader_url
            row.source_view_count = metadata.view_count
            row.source_duration_sec = metadata.duration_sec
            row.source_width = metadata.width
            row.source_height = metadata.height
            row.source_raw = metadata.raw

        return row
