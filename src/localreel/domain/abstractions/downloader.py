from abc import ABC, abstractmethod
from uuid import UUID


class AbstractDownloader(ABC):
    @abstractmethod
    def download(self, *, url: str, video_id: UUID) -> str:
        """Download the video and return the local path of the source file."""
        raise NotImplementedError
