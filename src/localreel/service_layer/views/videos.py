from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from localreel.service_layer.views.dtos import VideoCard


class VideoView:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def all_videos(self) -> list[VideoCard]:
        session = self._session_factory()
        try:
            rows = session.execute(
                text("""
                    SELECT
                        id,
                        source,
                        COALESCE(
                            title,
                            CASE source
                                WHEN 'FACEBOOK' THEN COALESCE(source_description, source_title)
                                ELSE COALESCE(source_title, source_description)
                            END
                        ) AS display_title,
                        thumbnail_path,
                        source_uploader AS uploader,
                        source_view_count,
                        duration_sec,
                        playback_path
                    FROM videos
                    WHERE status = 'READY'
                    ORDER BY id DESC
                """)
            )
            return [VideoCard.model_validate(dict(r._mapping)) for r in rows]
        finally:
            session.close()
