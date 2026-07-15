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
class DownloadVideo(Command):
    video_id: UUID
    url: str


@dataclass
class TranscodeVideo(Command):
    video_id: UUID
