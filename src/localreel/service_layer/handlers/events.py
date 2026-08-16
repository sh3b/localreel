from localreel.domain.downloader import AbstractDownloader
from localreel.domain.events import VideoCreated, VideoFailed, VideoUpdated
from localreel.domain.unit_of_work import AbstractUnitOfWork


class AddVideoHandler:
    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self._uow = uow

    def __call__(self, event: VideoCreated) -> None:
        self._uow.videos.add(event.video)


class SaveVideoHandler:
    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self._uow = uow

    def __call__(self, event: VideoUpdated) -> None:
        self._uow.videos.save(event.video)


class DiscardFilesHandler:
    def __init__(self, downloader: AbstractDownloader) -> None:
        self._downloader = downloader

    def __call__(self, event: VideoFailed) -> None:
        self._downloader.discard(video_id=event.video_id)
