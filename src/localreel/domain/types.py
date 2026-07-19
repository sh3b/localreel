from enum import StrEnum
from urllib.parse import urlsplit

from localreel.domain.exceptions import UnsupportedSource


class VideoStatus(StrEnum):
    PENDING = "PENDING"


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
            for domain, source in SOURCE_DOMAINS.items():
                if host == domain or host.endswith("." + domain):
                    return source
        raise UnsupportedSource(f"Unsupported video source: {url}")


# Hosts yt-dlp has a dedicated extractor for. No fb.watch: only yt-dlp's
# generic extractor follows those short links.
SOURCE_DOMAINS = {
    "youtube.com": VideoSource.YOUTUBE,
    "youtu.be": VideoSource.YOUTUBE,
    "youtube-nocookie.com": VideoSource.YOUTUBE,
    "tiktok.com": VideoSource.TIKTOK,
    "facebook.com": VideoSource.FACEBOOK,
}
