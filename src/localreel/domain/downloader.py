from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from localreel.domain.value_objects import SourceMetadata


@dataclass(frozen=True)
class DownloadResult:
    file_path: str
    thumbnail_path: str | None
    metadata: SourceMetadata


class AbstractDownloader(ABC):
    @abstractmethod
    def download(self, *, url: str, video_id: UUID) -> DownloadResult:
        """Downloads the video; paths are relative to the downloads directory."""
        raise NotImplementedError

    @abstractmethod
    def discard(self, *, video_id: UUID) -> None:
        """Deletes every file the video's downloads left, finished or not."""
        raise NotImplementedError
