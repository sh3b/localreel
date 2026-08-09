import logging

from localreel.domain.commands import MarkFailed, MarkReady, StartDownload
from localreel.domain.downloader import AbstractDownloader
from localreel.domain.exceptions import InvalidStatusTransition
from localreel.domain.unit_of_work import AbstractUnitOfWork
from localreel.service_layer.message_bus import MessageBus

logger = logging.getLogger(__name__)


class DownloadService:
    def __init__(
        self,
        *,
        uow: AbstractUnitOfWork,
        message_bus: MessageBus,
        downloader: AbstractDownloader,
    ) -> None:
        self._uow = uow
        self._bus = message_bus
        self._downloader = downloader

    def download_next(self) -> bool:
        with self._uow:
            video = self._uow.videos.next_pending()
        if video is None:
            return False

        try:
            with self._uow:
                self._bus.handle(StartDownload(video_id=video.id))
        except InvalidStatusTransition:
            logger.info("video %s was already taken", video.id)
            return True

        command: MarkReady | MarkFailed
        try:
            file_path = self._downloader.download(
                url=video.source_url, video_id=video.id
            )
        except Exception as exc:
            logger.exception("download failed for video %s", video.id)
            command = MarkFailed(video_id=video.id, reason=str(exc))
        else:
            command = MarkReady(video_id=video.id, file_path=file_path)

        with self._uow:
            self._bus.handle(command)
        return True
