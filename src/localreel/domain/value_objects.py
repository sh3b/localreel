import re
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar
from urllib.parse import parse_qs, urlsplit

from localreel.domain.exceptions import UnsupportedSource


class VideoStatus(StrEnum):
    PENDING = "PENDING"
    DOWNLOADING = "DOWNLOADING"
    READY = "READY"
    FAILED = "FAILED"


class VideoSource(StrEnum):
    YOUTUBE = "YOUTUBE"
    TIKTOK = "TIKTOK"
    FACEBOOK = "FACEBOOK"

    @classmethod
    def from_url(cls, url: str) -> VideoSource:
        # The parsed host, not substrings: whatever passes here is fetched
        # from inside the server's network.
        parts = urlsplit(url)
        try:
            port = parts.port
        except ValueError as exc:
            raise UnsupportedSource(f"Unsupported video source: {url}") from exc
        host = parts.hostname or ""
        # No userinfo: URL parsers disagree on where the host starts around "@".
        if (
            parts.scheme in ("http", "https")
            and "@" not in parts.netloc
            and port in (None, 80 if parts.scheme == "http" else 443)
        ):
            for source in cls:
                if any(host == d or host.endswith("." + d) for d in source.domains):
                    return source
        raise UnsupportedSource(f"Unsupported video source: {url}")

    @property
    def domains(self) -> tuple[str, ...]:
        """Hosts yt-dlp has a dedicated extractor for. No fb.watch: only
        yt-dlp's generic extractor follows those short links."""
        match self:
            case VideoSource.YOUTUBE:
                return ("youtube.com", "youtu.be", "youtube-nocookie.com")
            case VideoSource.TIKTOK:
                return ("tiktok.com",)
            case VideoSource.FACEBOOK:
                return ("facebook.com",)


@dataclass(frozen=True)
class SourceURL:
    """A submitted URL plus the key that identifies its video: two URLs with
    the same key are the same video."""

    url: str
    source: VideoSource
    key: str

    _YOUTUBE_ID: ClassVar[re.Pattern[str]] = re.compile(r"[A-Za-z0-9_-]{11}")
    _YOUTUBE_PATH_PREFIXES: ClassVar[tuple[str, ...]] = ("shorts", "embed", "live", "v")

    @classmethod
    def parse(cls, url: str) -> SourceURL:
        source = VideoSource.from_url(url)
        parts = urlsplit(url)
        if source is VideoSource.YOUTUBE:
            key = f"youtube:{cls._youtube_id(url)}"
        else:
            host = (parts.hostname or "").removeprefix("www.").removeprefix("m.")
            query = f"?{parts.query}" if parts.query else ""
            key = f"https://{host}{parts.path}{query}"
        return cls(url=url, source=source, key=key)

    @classmethod
    def _youtube_id(cls, url: str) -> str:
        # Rejects channels, playlists and the like: they aren't one video.
        parts = urlsplit(url)
        segments = [s for s in parts.path.split("/") if s]
        candidate = ""
        if parts.hostname == "youtu.be" and segments:
            candidate = segments[0]
        elif segments == ["watch"]:
            candidate = parse_qs(parts.query).get("v", [""])[0]
        elif len(segments) >= 2 and segments[0] in cls._YOUTUBE_PATH_PREFIXES:
            candidate = segments[1]
        if not cls._YOUTUBE_ID.fullmatch(candidate):
            raise UnsupportedSource(f"Not a YouTube video URL: {url}")
        return candidate
