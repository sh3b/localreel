from abc import ABC, abstractmethod
from uuid import UUID

from localreel.domain.models.video import Video


class AbstractVideoRepository(ABC):
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
    def next_pending(self) -> Video | None:
        """The oldest PENDING video, or None."""
        raise NotImplementedError

    @abstractmethod
    def save(self, video: Video) -> None:
        """Writes the changes to a video loaded with get."""
        raise NotImplementedError
