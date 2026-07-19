from uuid import uuid7

from localreel.domain.commands import SubmitURL
from localreel.domain.messages import Event
from localreel.domain.models.video import Video
from localreel.domain.unit_of_work import AbstractUnitOfWork
from localreel.domain.value_objects import SourceURL


class SubmitURLHandler:
    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self._uow = uow

    def __call__(self, cmd: SubmitURL) -> list[Event]:
        source_key = SourceURL.parse(cmd.url).key
        if self._uow.videos.exists(source_key=source_key):
            return []
        video = Video.create(id=uuid7(), source_url=cmd.url)
        return video.events
