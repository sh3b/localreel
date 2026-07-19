from uuid import UUID

from localreel.domain.events import VideoCreated
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
    ) -> None:
        self.id = id
        self.source = source
        self.source_url = source_url
        self.source_key = source_key
        self.status = status

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
        )
        video.events.append(VideoCreated(video))
        return video
