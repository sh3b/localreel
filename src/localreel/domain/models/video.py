from uuid import UUID

from localreel.domain.messages import Event
from localreel.domain.types import VideoSource, VideoStatus


class Video:
    def __init__(
        self,
        *,
        id: UUID,
        source: VideoSource,
        source_url: str,
        status: VideoStatus,
    ) -> None:
        self.id = id
        self.source = source
        self.source_url = source_url
        self.status = status

        self.events: list[Event] = []

    @classmethod
    def create(cls, *, id: UUID, source_url: str) -> Video:
        return cls(
            id=id,
            source=VideoSource.from_url(source_url),
            source_url=source_url,
            status=VideoStatus.PENDING,
        )
