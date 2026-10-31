import logging
from uuid import uuid7

from localreel.domain.commands import (
    MarkFailed,
    MarkReady,
    ResetDownload,
    RetryVideo,
    StartDownload,
    SubmitURL,
)
from localreel.domain.models.video import Video
from localreel.domain.unit_of_work import AbstractUnitOfWork
from localreel.domain.value_objects import SourceURL

logger = logging.getLogger(__name__)


class SubmitURLHandler:
    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self._uow = uow

    def __call__(self, cmd: SubmitURL) -> None:
        source_key = SourceURL.parse(cmd.url).key
        if self._uow.videos.exists(source_key=source_key):
            return
        video = Video.create(id=uuid7(), source_url=cmd.url)
        self._uow.videos.add(video)


class StartDownloadHandler:
    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self._uow = uow

    def __call__(self, cmd: StartDownload) -> None:
        video = self._uow.videos.get(cmd.video_id, lock=True)
        video.start_download()


class ResetDownloadHandler:
    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self._uow = uow

    def __call__(self, cmd: ResetDownload) -> None:
        video = self._uow.videos.get(cmd.video_id, lock=True)
        video.reset_download()
        logger.info(
            "video %s from %s was interrupted on attempt %s; now %s",
            video.id,
            video.source_url,
            video.attempts,
            video.status,
        )


class MarkReadyHandler:
    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self._uow = uow

    def __call__(self, cmd: MarkReady) -> None:
        video = self._uow.videos.get(cmd.video_id, lock=True)
        video.mark_ready(
            file_path=cmd.file_path,
            thumbnail_path=cmd.thumbnail_path,
            metadata=cmd.metadata,
        )
        logger.info(
            "video %s from %s is ready at %s",
            video.id,
            video.source_url,
            video.file_path,
        )


class MarkFailedHandler:
    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self._uow = uow

    def __call__(self, cmd: MarkFailed) -> None:
        video = self._uow.videos.get(cmd.video_id, lock=True)
        video.mark_failed(cmd.reason)


class RetryVideoHandler:
    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self._uow = uow

    def __call__(self, cmd: RetryVideo) -> None:
        video = self._uow.videos.get(cmd.video_id, lock=True)
        video.retry()
