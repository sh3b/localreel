from abc import ABC, abstractmethod

from localreel.domain.models.video import Video


class AbstractVideoRepository(ABC):
    @abstractmethod
    def add(self, video: Video) -> None:
        raise NotImplementedError
