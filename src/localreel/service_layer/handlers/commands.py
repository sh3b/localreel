from uuid import uuid7

from localreel.domain.commands import MarkFailed, MarkReady, StartDownload, SubmitURL
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


class StartDownloadHandler:
    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self._uow = uow

    def __call__(self, cmd: StartDownload) -> list[Event]:
        video = self._uow.videos.get(cmd.video_id, lock=True)
        video.start_download()
        return video.events


class MarkReadyHandler:
    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self._uow = uow

    def __call__(self, cmd: MarkReady) -> list[Event]:
        video = self._uow.videos.get(cmd.video_id, lock=True)
        video.mark_ready(cmd.file_path)
        return video.events


class MarkFailedHandler:
    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self._uow = uow

    def __call__(self, cmd: MarkFailed) -> list[Event]:
        video = self._uow.videos.get(cmd.video_id, lock=True)
        video.mark_failed(cmd.reason)
        return video.events
