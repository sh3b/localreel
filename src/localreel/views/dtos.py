from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel

from localreel.domain.value_objects import VideoSource, VideoStatus


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


class QueueItem(BaseModel):
    id: UUID
    status: VideoStatus
    source_url: str
    error: str | None
    saved_at: datetime


class QueueTotals(BaseModel):
    pending: int
    downloading: int
    failed: int


class QueuePage(BaseModel):
    items: list[QueueItem]
    totals: QueueTotals


class SavedLink(BaseModel):
    id: UUID
    status: VideoStatus
    error: str | None
