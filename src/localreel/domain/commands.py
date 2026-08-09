from dataclasses import dataclass
from uuid import UUID

from localreel.domain.messages import Command


@dataclass(frozen=True)
class SubmitURL(Command):
    url: str


@dataclass(frozen=True)
class StartDownload(Command):
    video_id: UUID


@dataclass(frozen=True)
class MarkReady(Command):
    video_id: UUID
    file_path: str


@dataclass(frozen=True)
class MarkFailed(Command):
    video_id: UUID
    reason: str
