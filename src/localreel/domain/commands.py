from dataclasses import dataclass
from uuid import UUID

from localreel.domain.messages import Command
from localreel.domain.types import VideoVisibility


@dataclass
class SubmitURL(Command):
    url: str
    user_id: UUID
    visibility: VideoVisibility


@dataclass
class MarkDownloaded(Command):
    video_id: UUID
    original_path: str


@dataclass
class MarkFailed(Command):
    video_id: UUID
    reason: str


@dataclass
class TranscodeVideo(Command):
    video_id: UUID
