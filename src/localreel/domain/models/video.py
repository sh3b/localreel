from typing import ClassVar
from uuid import UUID

from localreel.domain.events import VideoFailed
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

        self.events: list[Event] = []

    @classmethod
    def create(cls, *, id: UUID, source_url: str) -> Video:
        parsed = SourceURL.parse(source_url)
        return cls(
            id=id,
            source=parsed.source,
            source_url=parsed.url,
            source_key=parsed.key,
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
