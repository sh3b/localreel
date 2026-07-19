from abc import ABC, abstractmethod
from uuid import UUID

from localreel.domain.models.video import Video


class AbstractVideoRepository(ABC):
    @abstractmethod
    def add(self, video: Video) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, video_id: UUID) -> Video:
        raise NotImplementedError

    @abstractmethod
    def get_by_source_url_hash(self, source_url_hash: str) -> Video | None:
        raise NotImplementedError
