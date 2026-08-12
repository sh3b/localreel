from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class TranscodeResult:
    playback_path: str
    thumbnail_path: str


class AbstractTranscoder(ABC):
    @abstractmethod
    def transcode(self, *, video_id: UUID, original_path: str) -> TranscodeResult:
        """Normalize the source into a browser-playable file plus a thumbnail."""
        raise NotImplementedError
