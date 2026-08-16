from dataclasses import dataclass
from uuid import UUID

from localreel.domain.messages import Event


@dataclass(frozen=True)
class VideoFailed(Event):
    video_id: UUID
