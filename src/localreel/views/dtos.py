from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from localreel.domain.value_objects import VideoSource


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
