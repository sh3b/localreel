from uuid import UUID

from pydantic import BaseModel


class VideoCard(BaseModel):
    id: UUID
    source: str
    display_title: str | None
    thumbnail_path: str | None
    uploader: str | None
    source_view_count: int | None
    duration_sec: int | None
    playback_path: str | None
