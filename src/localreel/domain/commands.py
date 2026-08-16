from dataclasses import dataclass
from uuid import UUID

from localreel.domain.messages import Command
from localreel.domain.value_objects import SourceMetadata


@dataclass(frozen=True)
class SubmitURL(Command):
    url: str


@dataclass(frozen=True)
class StartDownload(Command):
    video_id: UUID


@dataclass(frozen=True)
class ResetDownload(Command):
    video_id: UUID


@dataclass(frozen=True)
class MarkReady(Command):
    video_id: UUID
    file_path: str
    thumbnail_path: str | None
    metadata: SourceMetadata


@dataclass(frozen=True)
class MarkFailed(Command):
    video_id: UUID
    reason: str
