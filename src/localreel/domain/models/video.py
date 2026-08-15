from uuid import UUID

from localreel.domain.events import VideoCreated, VideoUpdated
from localreel.domain.exceptions import InvalidStatusTransition
from localreel.domain.messages import Event
from localreel.domain.value_objects import (
    SourceMetadata,
    SourceURL,
    VideoSource,
    VideoStatus,
)


class Video:
    def __init__(
        self,
        *,
        id: UUID,
        source: VideoSource,
        source_url: str,
        source_key: str,
        status: VideoStatus,
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
        self.file_path = file_path
        self.thumbnail_path = thumbnail_path
        self.source_metadata = source_metadata
        self.error = error

        self.events: list[Event] = []

    @classmethod
    def create(cls, *, id: UUID, source_url: str) -> Video:
        parsed = SourceURL.parse(source_url)
        video = cls(
            id=id,
            source=parsed.source,
            source_url=parsed.url,
            source_key=parsed.key,
            status=VideoStatus.PENDING,
            file_path=None,
            thumbnail_path=None,
            source_metadata=None,
            error=None,
        )
        video.events.append(VideoCreated(video))
        return video

    def start_download(self) -> None:
        self._transition(VideoStatus.PENDING, VideoStatus.DOWNLOADING)

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
        self._transition(VideoStatus.DOWNLOADING, VideoStatus.FAILED)
        self.error = reason

    def _transition(self, expected: VideoStatus, to: VideoStatus) -> None:
        if self.status is not expected:
            raise InvalidStatusTransition(
                f"Video {self.id} is {self.status}, not {expected}; cannot become {to}"
            )
        self.status = to
        self.events.append(VideoUpdated(self))
