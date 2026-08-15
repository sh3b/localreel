from dataclasses import dataclass
from uuid import UUID

from localreel.domain.messages import Command
from localreel.domain.types import VideoVisibility
from localreel.domain.value_objects.source_metadata import SourceMetadata


@dataclass
class SubmitURL(Command):
    url: str
    user_id: UUID
    visibility: VideoVisibility


@dataclass
class MarkDownloaded(Command):
    video_id: UUID
    original_path: str
    source_metadata: SourceMetadata | None = None


@dataclass
class MarkReady(Command):
    video_id: UUID
    playback_path: str
    thumbnail_path: str
    duration_sec: int | None = None
    width: int | None = None
    height: int | None = None


@dataclass
class MarkFailed(Command):
    video_id: UUID
    reason: str
