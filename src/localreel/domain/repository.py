from abc import ABC, abstractmethod
from uuid import UUID

from localreel.domain.models.video import Video


class AbstractVideoRepository(ABC):
    """Every video added or returned is tracked: the unit of work hands its
    events to the bus and saves it when it commits."""

    @abstractmethod
    def exists(self, *, source_key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def add(self, video: Video) -> None:
        """Raises DuplicateVideo if a video with the same source key exists."""
        raise NotImplementedError

    @abstractmethod
    def get(self, video_id: UUID, *, lock: bool) -> Video:
        """Raises VideoNotFound if no video has this id. With lock, the row
        stays locked until the unit of work ends."""
        raise NotImplementedError

    @abstractmethod
    def next_pending(self) -> UUID | None:
        """The id of the oldest PENDING video, or None."""
        raise NotImplementedError

    @abstractmethod
    def downloading(self) -> list[UUID]:
        """The ids of every DOWNLOADING video."""
        raise NotImplementedError
