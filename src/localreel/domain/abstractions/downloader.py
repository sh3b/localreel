from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from localreel.domain.value_objects.source_metadata import SourceMetadata


@dataclass(frozen=True)
class DownloadResult:
    original_path: str
    source_metadata: SourceMetadata


class AbstractDownloader(ABC):
    @abstractmethod
    def download(self, *, url: str, video_id: UUID) -> DownloadResult:
        """Download the video and describe where it came from."""
        raise NotImplementedError
