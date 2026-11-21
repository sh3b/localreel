from typing import ClassVar, get_args
from uuid import UUID

from sqlalchemy import ColumnElement, case, func, select
from sqlalchemy.orm import Session, sessionmaker

from localreel.adapters.orm import VideoORM
from localreel.domain.value_objects import VideoSource, VideoStatus
from localreel.views.dtos import (
    QueueItem,
    QueuePage,
    QueueStatus,
    QueueTotals,
    SavedLink,
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
                VideoORM.source_uploader_url,
                VideoORM.source_duration_sec,
                VideoORM.source_width,
                VideoORM.source_height,
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
                    uploader_url=row.source_uploader_url,
                    duration_sec=row.source_duration_sec,
                    width=row.source_width,
                    height=row.source_height,
                    source=row.source,
                    source_url=row.source_url,
                    saved_at=row.created_at,
                    playback_url=self._MEDIA_URL_PREFIX + row.file_path,
                    thumbnail_url=thumbnail_url,
                )
            )
        return VideoPage(items=cards, next_cursor=next_cursor)

    # Downloading and failed first: the video to watch and the ones to act on.
    # A limit then only ever cuts off videos that are waiting.
    _QUEUE_ORDER: ClassVar[ColumnElement[int]] = case(
        {VideoStatus.DOWNLOADING: 0, VideoStatus.FAILED: 1},
        value=VideoORM.status,
        else_=2,
    )

    def list_queue(self, *, limit: int) -> QueuePage:
        # Window functions run before the limit, so every row carries the
        # totals of the whole queue, read in the same snapshot as the rows.
        def total(status: VideoStatus) -> ColumnElement[int]:
            return func.count().filter(VideoORM.status == status).over()

        query = (
            select(
                VideoORM.id,
                VideoORM.status,
                VideoORM.source_url,
                VideoORM.error,
                VideoORM.created_at,
                total(VideoStatus.PENDING).label("pending"),
                total(VideoStatus.DOWNLOADING).label("downloading"),
                total(VideoStatus.FAILED).label("failed"),
            )
            .where(VideoORM.status.in_(get_args(QueueStatus)))
            .order_by(self._QUEUE_ORDER, VideoORM.id.desc())
            .limit(limit)
        )

        with self._session_factory() as session:
            rows = session.execute(query).all()

        if not rows:
            return QueuePage(
                items=[], totals=QueueTotals(pending=0, downloading=0, failed=0)
            )
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
        totals = QueueTotals(
            pending=rows[0].pending,
            downloading=rows[0].downloading,
            failed=rows[0].failed,
        )
        return QueuePage(items=items, totals=totals)

    def saved_links(self, source_keys: list[str]) -> dict[str, SavedLink]:
        query = select(
            VideoORM.source_key, VideoORM.id, VideoORM.status, VideoORM.error
        ).where(
            VideoORM.source_key.in_(source_keys),
            # A REMOVED video waiting for cleanup is not what the link is now.
            VideoORM.status != VideoStatus.REMOVED,
        )

        with self._session_factory() as session:
            rows = session.execute(query).all()

        return {
            row.source_key: SavedLink(id=row.id, status=row.status, error=row.error)
            for row in rows
        }
