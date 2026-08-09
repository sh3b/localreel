from abc import ABC, abstractmethod
from uuid import UUID


class AbstractDownloader(ABC):
    @abstractmethod
    def download(self, *, url: str, video_id: UUID) -> str:
        """Downloads the video and returns the path of the saved file."""
        raise NotImplementedError
