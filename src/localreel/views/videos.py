from datetime import UTC, datetime
from typing import ClassVar

from sqlalchemy import ColumnElement, case, func, select
from sqlalchemy.orm import Session, sessionmaker

from localreel.adapters.orm import VideoORM
from localreel.domain.value_objects import VideoSource, VideoStatus
from localreel.views.dtos import VideoCard


class VideoView:
    _MEDIA_URL_PREFIX: ClassVar[str] = "/media/"

    _TITLE: ClassVar[ColumnElement[str | None]] = case(
        (
            VideoORM.source == VideoSource.FACEBOOK,
            func.coalesce(VideoORM.source_description, VideoORM.source_title),
        ),
        else_=func.coalesce(VideoORM.source_title, VideoORM.source_description),
    )

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_videos(self) -> list[VideoCard]:
        query = (
            select(
                VideoORM.id,
                self._TITLE.label("title"),
                VideoORM.source_uploader,
                VideoORM.source_duration_sec,
                VideoORM.source,
                VideoORM.source_url,
                VideoORM.file_path,
                VideoORM.thumbnail_path,
            )
            .where(VideoORM.status == VideoStatus.READY)
            .order_by(VideoORM.id.desc())
        )
        with self._session_factory() as session:
            rows = session.execute(query).all()

        cards = []
        for row in rows:
            thumbnail_url = None
            if row.thumbnail_path is not None:
                thumbnail_url = self._MEDIA_URL_PREFIX + row.thumbnail_path
            cards.append(
                VideoCard(
                    id=row.id,
                    title=row.title,
                    uploader=row.source_uploader,
                    duration_sec=row.source_duration_sec,
                    source=row.source,
                    source_url=row.source_url,
                    saved_at=datetime.fromtimestamp(row.id.time / 1000, UTC),
                    playback_url=self._MEDIA_URL_PREFIX + row.file_path,
                    thumbnail_url=thumbnail_url,
                )
            )
        return cards
