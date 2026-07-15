from enum import StrEnum

from localreel.domain.exceptions import UnsupportedSource


class VideoStatus(StrEnum):
    PENDING = "PENDING"
    DOWNLOADING = "DOWNLOADING"
    DOWNLOADED = "DOWNLOADED"
    TRANSCODING = "TRANSCODING"
    READY = "READY"
    FAILED = "FAILED"


class VideoSource(StrEnum):
    YOUTUBE = "YOUTUBE"
    TIKTOK = "TIKTOK"
    FACEBOOK = "FACEBOOK"
    LOCAL = "LOCAL"

    @classmethod
    def from_url(cls, url: str) -> VideoSource:
        u = url.lower()
        if "youtube.com" in u or "youtu.be" in u:
            return cls.YOUTUBE
        if "tiktok.com" in u:
            return cls.TIKTOK
        if "facebook.com" in u or "fb.watch" in u:
            return cls.FACEBOOK
        raise UnsupportedSource(f"Unsupported video source: {url}")


class VideoVisibility(StrEnum):
    PRIVATE = "PRIVATE"  # only the owner (uploaded_by) sees it
    SHARED = "SHARED"  # visible to all logged-in members
