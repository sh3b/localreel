from typing import ClassVar
from uuid import UUID

from sqlalchemy import ColumnElement, case, func, select
from sqlalchemy.orm import Session, sessionmaker

from localreel.adapters.orm import VideoORM
from localreel.domain.value_objects import VideoSource, VideoStatus
from localreel.views.dtos import (
    QueueItem,
    QueuePage,
    VideoCard,
    VideoPage,
    VideoSort,
)


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

    def list_videos(
        self, *, sort: VideoSort, after: UUID | None, limit: int
    ) -> VideoPage:
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
                VideoORM.created_at,
            )
            .where(VideoORM.status == VideoStatus.READY)
            .limit(limit + 1)
        )
        if sort is VideoSort.NEWEST:
            query = query.order_by(VideoORM.id.desc())
            if after is not None:
                query = query.where(VideoORM.id < after)
        else:
            query = query.order_by(VideoORM.id.asc())
            if after is not None:
                query = query.where(VideoORM.id > after)

        with self._session_factory() as session:
            rows = session.execute(query).all()

        next_cursor = None
        if len(rows) > limit:
            rows = rows[:limit]
            next_cursor = rows[-1].id

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
                    saved_at=row.created_at,
                    playback_url=self._MEDIA_URL_PREFIX + row.file_path,
                    thumbnail_url=thumbnail_url,
                )
            )
        return VideoPage(items=cards, next_cursor=next_cursor)

    def list_queue(self, *, after: UUID | None, limit: int) -> QueuePage:
        query = (
            select(
                VideoORM.id,
                VideoORM.status,
                VideoORM.source_url,
                VideoORM.error,
                VideoORM.created_at,
            )
            .where(VideoORM.status != VideoStatus.READY)
            .order_by(VideoORM.id.desc())
            .limit(limit + 1)
        )
        if after is not None:
            query = query.where(VideoORM.id < after)

        with self._session_factory() as session:
            rows = session.execute(query).all()

        next_cursor = None
        if len(rows) > limit:
            rows = rows[:limit]
            next_cursor = rows[-1].id

        items = [
            QueueItem(
                id=row.id,
                status=row.status,
                source_url=row.source_url,
                error=row.error,
                saved_at=row.created_at,
            )
            for row in rows
        ]
        return QueuePage(items=items, next_cursor=next_cursor)
