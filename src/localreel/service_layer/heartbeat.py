import logging
import threading
from datetime import UTC, datetime, timedelta
from types import TracebackType
from typing import Self
from uuid import UUID

from localreel.domain.abstractions.unit_of_work import AbstractUnitOfWork
from localreel.domain.commands import MarkFailed, RecordHeartbeat
from localreel.domain.types import VideoStatus
from localreel.service_layer.message_bus import MessageBus

logger = logging.getLogger(__name__)


class Heartbeat:
    """Record a heartbeat for one video every interval while the block runs.

    The beats come from a background thread, each in its own short transaction,
    so the slow work in the block still holds no transaction. They stop when the
    block exits; a process that dies stops them too, which is what the sweep
    looks for.
    """

    def __init__(
        self,
        uow: AbstractUnitOfWork,
        message_bus: MessageBus,
        video_id: UUID,
        interval_sec: float,
    ) -> None:
        self._uow = uow
        self._message_bus = message_bus
        self._video_id = video_id
        self._interval_sec = interval_sec
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def __enter__(self) -> Self:
        self._thread.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._stop.set()
        self._thread.join()

    def _run(self) -> None:
        while not self._stop.wait(self._interval_sec):
            # One failed beat (the database briefly away) must not end the
            # beats: a job that stops beating gets swept.
            try:
                with self._uow:
                    self._message_bus.handle(RecordHeartbeat(video_id=self._video_id))
            except Exception:
                logger.exception("heartbeat failed for video %s", self._video_id)


def fail_stalled(
    uow: AbstractUnitOfWork,
    message_bus: MessageBus,
    status: VideoStatus,
    stalled_after_sec: float,
) -> None:
    """Mark failed every video in `status` whose worker stopped beating.

    A worker that dies mid-job (SIGKILL, out of memory, power cut) leaves its
    video in `status` with nothing to move it on. Failed, not pending: a video
    that kills its worker would otherwise be claimed and kill it forever.
    Retrying it is left to the user.
    """
    beat_before = datetime.now(UTC) - timedelta(seconds=stalled_after_sec)
    with uow:
        for video in uow.videos.get_stalled(status, beat_before):
            logger.warning(
                "video %s stalled in %s, marking it failed", video.id, status
            )
            message_bus.handle(MarkFailed(video_id=video.id, reason="worker stalled"))
