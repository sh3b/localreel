from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class VideoSort(StrEnum):
    NEWEST = "newest"
    OLDEST = "oldest"


class VideoCard(BaseModel):
    id: UUID
    source: str
    title: str | None
    uploader: str | None
    tags: list[str]
    duration_sec: int | None
    width: int | None
    height: int | None
    source_url: str | None
    source_view_count: int | None
    saved_at: datetime
    playback_url: str | None
    thumbnail_url: str | None


class VideoPage(BaseModel):
    items: list[VideoCard]
    next_cursor: UUID | None
