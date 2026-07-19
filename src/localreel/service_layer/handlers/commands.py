from uuid import uuid7

from localreel.domain.commands import SubmitURL
from localreel.domain.messages import Event
from localreel.domain.models.video import Video


class SubmitURLHandler:
    def __call__(self, cmd: SubmitURL) -> list[Event]:
        video = Video.create(id=uuid7(), source_url=cmd.url)
        return video.events
