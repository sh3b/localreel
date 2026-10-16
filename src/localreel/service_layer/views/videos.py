from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from localreel.service_layer.views.dtos import VideoCard, VideoPage, VideoSort

# Must match `location /media/` in nginx.conf, which serves MEDIA_DIR.
MEDIA_URL_PREFIX = "/media/"


class VideoView:
    # Keyset pagination on id. Ids are UUIDv7, so id order is creation order.
    _KEYSET: dict[VideoSort, tuple[str, str]] = {
        VideoSort.NEWEST: ("<", "DESC"),
        VideoSort.OLDEST: (">", "ASC"),
    }

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_videos(self, sort: VideoSort, after: UUID | None, limit: int) -> VideoPage:
        operator, direction = self._KEYSET[sort]
        session = self._session_factory()
        try:
            rows = session.execute(
                text(f"""
                    SELECT
                        id,
                        source,
                        COALESCE(
                            title,
                            CASE source
                                WHEN 'FACEBOOK' THEN COALESCE(source_description, source_title)
                                ELSE COALESCE(source_title, source_description)
                            END
                        ) AS title,
                        source_uploader AS uploader,
                        tags,
                        duration_sec,
                        width,
                        height,
                        source_url,
                        source_view_count,
                        playback_path,
                        thumbnail_path
                    FROM videos
                    WHERE status = 'READY'
                      AND (CAST(:after AS uuid) IS NULL OR id {operator} :after)
                    ORDER BY id {direction}
                    LIMIT :fetch
                """),
                # One extra row tells us whether another page exists.
                {"after": after, "fetch": limit + 1},
            )
            cards = [self.to_card(r._mapping) for r in rows]
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
