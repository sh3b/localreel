from uuid import UUID

from localreel.domain.events import VideoCreated, VideoUpdated
from localreel.domain.exceptions import InvalidStatusTransition
from localreel.domain.messages import Event
from localreel.domain.value_objects import SourceURL, VideoSource, VideoStatus


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
        error: str | None,
    ) -> None:
        self.id = id
        self.source = source
        self.source_url = source_url
        self.source_key = source_key
        self.status = status
        self.file_path = file_path
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
            error=None,
        )
        video.events.append(VideoCreated(video))
        return video

    def start_download(self) -> None:
        self._transition(VideoStatus.PENDING, VideoStatus.DOWNLOADING)

    def mark_ready(self, file_path: str) -> None:
        self._transition(VideoStatus.DOWNLOADING, VideoStatus.READY)
        self.file_path = file_path

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
