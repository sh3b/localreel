from typing import ClassVar
from uuid import UUID

from localreel.domain.events import VideoFailed, VideoRemoved
from localreel.domain.exceptions import InvalidStatusTransition
from localreel.domain.messages import Event
from localreel.domain.value_objects import (
    SourceMetadata,
    SourceURL,
    VideoSource,
    VideoStatus,
)


class Video:
    _MAX_ATTEMPTS: ClassVar[int] = 3
    # A downloading video is the worker's until it is ready or failed.
    _REMOVABLE: ClassVar[frozenset[VideoStatus]] = frozenset(
        {VideoStatus.PENDING, VideoStatus.FAILED}
    )

    def __init__(
        self,
        *,
        id: UUID,
        source: VideoSource,
        source_url: str,
        source_key: str,
        status: VideoStatus,
        attempts: int,
        file_path: str | None,
        thumbnail_path: str | None,
        source_metadata: SourceMetadata | None,
        error: str | None,
    ) -> None:
        self.id = id
        self.source = source
        self.source_url = source_url
        self.source_key = source_key
        self.status = status
        self.attempts = attempts
        self.file_path = file_path
        self.thumbnail_path = thumbnail_path
        self.source_metadata = source_metadata
        self.error = error

        self.removed = False
        self.events: list[Event] = []

    @classmethod
    def create(cls, *, id: UUID, source_url: SourceURL) -> Video:
        return cls(
            id=id,
            source=source_url.source,
            source_url=source_url.url,
            source_key=source_url.key,
            status=VideoStatus.PENDING,
            attempts=0,
            file_path=None,
            thumbnail_path=None,
            source_metadata=None,
            error=None,
        )

    def start_download(self) -> None:
        self._transition(VideoStatus.PENDING, VideoStatus.DOWNLOADING)
        self.attempts += 1

    def mark_ready(
        self,
        *,
        file_path: str,
        thumbnail_path: str | None,
        metadata: SourceMetadata,
    ) -> None:
        self._transition(VideoStatus.DOWNLOADING, VideoStatus.READY)
        self.file_path = file_path
        self.thumbnail_path = thumbnail_path
        self.source_metadata = metadata

    def mark_failed(self, reason: str) -> None:
        self._fail(reason)

    def reset_download(self) -> None:
        if self.attempts >= self._MAX_ATTEMPTS:
            self._fail(f"Download interrupted {self.attempts} times")
            return
        self._transition(VideoStatus.DOWNLOADING, VideoStatus.PENDING)

    def retry(self) -> None:
        self._transition(VideoStatus.FAILED, VideoStatus.PENDING)
        self.attempts = 0
        self.error = None

    def remove(self) -> None:
        if self.status not in self._REMOVABLE:
            raise InvalidStatusTransition(
                f"Video {self.id} is {self.status}; only a PENDING or FAILED "
                "video can be removed"
            )
        self.removed = True
        # A PENDING video can hold the part files of an interrupted download.
        self.events.append(VideoRemoved(video_id=self.id))

    def collect_events(self) -> list[Event]:
        # Empty the list on handover: the unit of work collects after every
        # handler, and the video stays tracked, so the next collection would
        # hand these events over again.
        events = self.events
        self.events = []
        return events

    def _fail(self, reason: str) -> None:
        self._transition(VideoStatus.DOWNLOADING, VideoStatus.FAILED)
        self.error = reason
        self.events.append(VideoFailed(video_id=self.id))

    def _transition(self, expected: VideoStatus, to: VideoStatus) -> None:
        if self.status is not expected:
            raise InvalidStatusTransition(
                f"Video {self.id} is {self.status}, expected {expected}; cannot become {to}"
            )
        self.status = to
