from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, sessionmaker

from localreel.adapters.orm import videos
from localreel.domain.types import VideoSource, VideoStatus
from localreel.views.dtos import VideoCard, VideoPage, VideoSort

# Must match `location /media/` in nginx.conf, which serves MEDIA_DIR.
MEDIA_URL_PREFIX = "/media/"


class VideoView:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_videos(self, sort: VideoSort, after: UUID | None, limit: int) -> VideoPage:
        title = func.coalesce(
            videos.c.title,
            case(
                (
                    videos.c.source == VideoSource.FACEBOOK,
                    func.coalesce(videos.c.source_description, videos.c.source_title),
                ),
                else_=func.coalesce(videos.c.source_title, videos.c.source_description),
            ),
        )
        query = (
            select(
                videos.c.id,
                videos.c.source,
                title.label("title"),
                videos.c.source_uploader.label("uploader"),
                videos.c.tags,
                videos.c.duration_sec,
                videos.c.width,
                videos.c.height,
                videos.c.source_url,
                videos.c.source_view_count,
                videos.c.playback_path,
                videos.c.thumbnail_path,
            )
            .where(videos.c.status == VideoStatus.READY)
            # One extra row tells us whether another page exists.
            .limit(limit + 1)
        )
        # Keyset pagination on id. Ids are UUIDv7, so id order is creation order.
        if sort is VideoSort.NEWEST:
            query = query.order_by(videos.c.id.desc())
            if after is not None:
                query = query.where(videos.c.id < after)
        else:
            query = query.order_by(videos.c.id.asc())
            if after is not None:
                query = query.where(videos.c.id > after)

        session = self._session_factory()
        try:
            cards = [self.to_card(r._mapping) for r in session.execute(query)]
        finally:
            session.close()

        items = cards[:limit]
        next_cursor = items[-1].id if len(cards) > limit else None
        return VideoPage(items=items, next_cursor=next_cursor)

    @staticmethod
    def to_card(row: Mapping[Any, Any]) -> VideoCard:
        video_id: UUID = row["id"]
        playback_path: str | None = row["playback_path"]
        thumbnail_path: str | None = row["thumbnail_path"]
        return VideoCard(
            id=video_id,
            source=row["source"],
            title=row["title"],
            uploader=row["uploader"],
            tags=row["tags"],
            duration_sec=row["duration_sec"],
            width=row["width"],
            height=row["height"],
            source_url=row["source_url"],
            source_view_count=row["source_view_count"],
            # Ids are UUIDv7: the first 48 bits are the creation time in Unix ms.
            saved_at=datetime.fromtimestamp(video_id.time / 1000, UTC),
            playback_url=MEDIA_URL_PREFIX + playback_path if playback_path else None,
            thumbnail_url=MEDIA_URL_PREFIX + thumbnail_path if thumbnail_path else None,
        )
