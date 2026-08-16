from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from localreel.domain.messages import Event

if TYPE_CHECKING:
    from localreel.domain.models.video import Video


@dataclass(frozen=True)
class VideoCreated(Event):
    video: Video


@dataclass(frozen=True)
class VideoUpdated(Event):
    video: Video


@dataclass(frozen=True)
class VideoFailed(Event):
    video_id: UUID
