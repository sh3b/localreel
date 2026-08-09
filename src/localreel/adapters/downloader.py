from pathlib import Path
from typing import Any
from uuid import UUID

from yt_dlp import YoutubeDL

from localreel.domain.downloader import AbstractDownloader


class YtDlpDownloader(AbstractDownloader):
    def __init__(self, downloads_dir: Path) -> None:
        self._downloads_dir = downloads_dir

    def download(self, *, url: str, video_id: UUID) -> str:
        with YoutubeDL(self._options(video_id)) as ydl:
            info = ydl.extract_info(url, download=True)
        return str(info["requested_downloads"][0]["filepath"])

    def _options(self, video_id: UUID) -> dict[str, Any]:
        return {
            "outtmpl": str(self._downloads_dir / f"{video_id}.%(ext)s"),
            "allowed_extractors": [
                "youtube.*",
                "tiktok.*",
                r"vm\.tiktok",
                "facebook.*",
            ],
            "quiet": True,
            "noprogress": True,
        }
