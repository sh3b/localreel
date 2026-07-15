from dataclasses import dataclass
from uuid import UUID

from localreel.domain.messages import Event


@dataclass
class VideoIngested(Event):
    video_id: UUID


@dataclass
class VideoDownloaded(Event):
    video_id: UUID


@dataclass
class VideoReady(Event):
    video_id: UUID


@dataclass
class VideoFailed(Event):
    video_id: UUID
    reason: str


@dataclass
class WatchRecorded(Event):
    video_id: UUID
    user_id: UUID
    tags: list[str]


@dataclass
class TagsUpdated(Event):
    video_id: UUID
    tags: list[str]  # final tag set after the update
    tags_added: list[str]
    tags_removed: list[str]


@dataclass
class SourceFileRemoved(Event):
    video_id: UUID
