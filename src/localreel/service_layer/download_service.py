import logging

from localreel.domain.commands import (
    MarkFailed,
    MarkReady,
    PurgeVideo,
    ResetDownload,
    StartDownload,
)
from localreel.domain.downloader import AbstractDownloader
from localreel.domain.exceptions import DownloadFailed, InvalidStatusTransition
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

    def reset_interrupted_downloads(self) -> None:
        with self._uow(commit=False):
            video_ids = self._uow.videos.downloading()
        for video_id in video_ids:
            with self._uow:
                self._bus.handle(ResetDownload(video_id=video_id))

    def purge_removed(self) -> None:
        # Removing a video only marks it. Its files are deleted here, outside
        # any transaction, and only then its row, so a crash in between leaves
        # a hidden row whose files are already gone; the next pass finishes it.
        with self._uow(commit=False):
            video_ids = self._uow.videos.removed()
        for video_id in video_ids:
            try:
                self._downloader.discard(video_id=video_id)
                with self._uow:
                    self._bus.handle(PurgeVideo(video_id=video_id))
            except Exception:
                logger.exception("could not purge video %s; trying again", video_id)

    def download_next(self) -> bool:
        # Pick: read only.
        with self._uow(commit=False):
            video_id = self._uow.videos.next_pending()
            if video_id is None:
                return False
            source_url = self._uow.videos.get(video_id, lock=False).source_url

        # Claim: committed before the download, so a crash leaves a row to recover.
        try:
            with self._uow:
                self._bus.handle(StartDownload(video_id=video_id))
        except InvalidStatusTransition:
            logger.info("video %s was taken or removed meanwhile", video_id)
            return True

        # Download: outside any transaction, it takes time.
        command: MarkReady | MarkFailed
        try:
            result = self._downloader.download(url=source_url, video_id=video_id)
        except DownloadFailed as exc:
            # Expected: the site refused the video (unavailable, private,
            # blocked). A traceback for it would only bury real errors.
            logger.warning("download failed for video %s: %s", video_id, exc)
            command = MarkFailed(video_id=video_id, reason=str(exc))
        except Exception as exc:
            logger.exception("download failed for video %s", video_id)
            command = MarkFailed(video_id=video_id, reason=str(exc))
        else:
            command = MarkReady(
                video_id=video_id,
                file_path=result.file_path,
                thumbnail_path=result.thumbnail_path,
                metadata=result.metadata,
            )

        # Record: READY or FAILED.
        with self._uow:
            self._bus.handle(command)
        return True
