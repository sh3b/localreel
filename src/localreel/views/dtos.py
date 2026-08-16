from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel

from localreel.domain.value_objects import VideoSource


class VideoSort(StrEnum):
    NEWEST = "newest"
    OLDEST = "oldest"


class VideoCard(BaseModel):
    id: UUID
    title: str | None
    uploader: str | None
    duration_sec: int | None
    source: VideoSource
    source_url: str
    saved_at: datetime
    playback_url: str
    thumbnail_url: str | None


class VideoPage(BaseModel):
    items: list[VideoCard]
    next_cursor: UUID | None
