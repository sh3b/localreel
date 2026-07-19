from dataclasses import dataclass
from typing import TYPE_CHECKING

from localreel.domain.messages import Event

if TYPE_CHECKING:
    from localreel.domain.models.video import Video


@dataclass(frozen=True)
class VideoCreated(Event):
    video: Video
