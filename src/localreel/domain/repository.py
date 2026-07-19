from abc import ABC, abstractmethod

from localreel.domain.models.video import Video


class AbstractVideoRepository(ABC):
    @abstractmethod
    def exists(self, *, source_key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def add(self, video: Video) -> None:
        """Raises DuplicateVideo if a video with the same source key exists."""
        raise NotImplementedError
