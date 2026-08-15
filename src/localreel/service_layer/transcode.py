import logging
from uuid import UUID

from localreel.domain.abstractions.transcoder import AbstractTranscoder
from localreel.domain.abstractions.unit_of_work import AbstractUnitOfWork
from localreel.domain.commands import MarkFailed, MarkReady
from localreel.service_layer.message_bus import MessageBus

logger = logging.getLogger(__name__)


def transcode_next_downloaded(
    uow: AbstractUnitOfWork,
    message_bus: MessageBus,
    transcoder: AbstractTranscoder,
) -> bool:
    """Claim one downloaded video, normalize it, and persist the outcome.

    Returns False when there was nothing to claim, so the caller can back off.
    ffmpeg is slow and CPU-bound, so it runs between two short transactions,
    holding no row lock and no connection of its own.
    """
    claimed = _claim_next(uow)
    if claimed is None:
        return False
    video_id, original_path = claimed
    outcome: MarkReady | MarkFailed = _transcode(transcoder, video_id, original_path)
    with uow:
        message_bus.handle(outcome)
    return True


def _claim_next(uow: AbstractUnitOfWork) -> tuple[UUID, str] | None:
    with uow:
        video = uow.videos.get_next_downloaded()
        if video is None:
            return None
        video.mark_transcoding()
        # original_path is set by mark_downloaded, which is the only way into
        # the DOWNLOADED status the claim query selects on.
        if video.original_path is None:
            raise RuntimeError(f"claimed video {video.id} with no original_path")
        return video.id, video.original_path


def _transcode(
    transcoder: AbstractTranscoder, video_id: UUID, original_path: str
) -> MarkReady | MarkFailed:
    try:
        result = transcoder.transcode(video_id=video_id, original_path=original_path)
    except Exception as exc:
        logger.exception("transcode failed for video %s", video_id)
        return MarkFailed(video_id=video_id, reason=str(exc))
    return MarkReady(
        video_id=video_id,
        playback_path=result.playback_path,
        thumbnail_path=result.thumbnail_path,
        duration_sec=result.duration_sec,
        width=result.width,
        height=result.height,
    )
