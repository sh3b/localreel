import logging
from uuid import UUID

from localreel.domain.abstractions.downloader import AbstractDownloader
from localreel.domain.abstractions.unit_of_work import AbstractUnitOfWork
from localreel.domain.commands import MarkDownloaded, MarkFailed
from localreel.domain.exceptions import InvalidStatusTransition
from localreel.service_layer.heartbeat import Heartbeat
from localreel.service_layer.message_bus import MessageBus

logger = logging.getLogger(__name__)


def download_next_pending(
    uow: AbstractUnitOfWork,
    message_bus: MessageBus,
    downloader: AbstractDownloader,
    heartbeat_interval_sec: float,
) -> bool:
    """Claim one pending video, download it, and persist the outcome.

    Returns False when there was nothing to claim, so the caller can back off.
    The slow download runs between two short transactions, holding no lock and
    no open transaction of its own — that is why it lives here and not inside a
    command handler.

    If the process is told to stop mid-download (SIGTERM becomes `SystemExit`,
    Ctrl-C is `KeyboardInterrupt`), the video is marked failed before the
    interruption propagates, so it is not stranded in `DOWNLOADING`. A worker
    killed outright can't do that; its heartbeat stops instead, and
    `fail_stalled` marks the video failed.
    """
    claimed = _claim_next(uow)
    if claimed is None:
        return False
    video_id, url = claimed
    try:
        with Heartbeat(uow, message_bus, video_id, heartbeat_interval_sec):
            outcome: MarkDownloaded | MarkFailed = _download(downloader, video_id, url)
    except SystemExit, KeyboardInterrupt:
        _persist(
            uow, message_bus, MarkFailed(video_id=video_id, reason="worker shut down")
        )
        raise
    _persist(uow, message_bus, outcome)
    return True


def _claim_next(uow: AbstractUnitOfWork) -> tuple[UUID, str] | None:
    with uow:
        video = uow.videos.get_next_pending()
        if video is None:
            return None
        video.mark_downloading()
        # source_url is non-None here: the claim query excludes LOCAL, and every
        # remote video is created with its URL set.
        if video.source_url is None:
            raise RuntimeError(f"claimed non-LOCAL video {video.id} with no source_url")
        return video.id, video.source_url


def _persist(
    uow: AbstractUnitOfWork,
    message_bus: MessageBus,
    outcome: MarkDownloaded | MarkFailed,
) -> None:
    try:
        with uow:
            message_bus.handle(outcome)
    except InvalidStatusTransition:
        # The sweep failed the video while this download ran (its beats were
        # late), so the video is no longer ours to finish.
        logger.warning("dropped a late outcome for video %s", outcome.video_id)


def _download(
    downloader: AbstractDownloader, video_id: UUID, url: str
) -> MarkDownloaded | MarkFailed:
    try:
        result = downloader.download(url=url, video_id=video_id)
    except Exception as exc:
        logger.exception("download failed for video %s", video_id)
        return MarkFailed(video_id=video_id, reason=str(exc))
    return MarkDownloaded(
        video_id=video_id,
        original_path=result.original_path,
        source_metadata=result.source_metadata,
    )
