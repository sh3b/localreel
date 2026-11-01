from pathlib import Path
from typing import Any, ClassVar
from uuid import UUID

from yt_dlp import YoutubeDL

from localreel.domain.downloader import AbstractDownloader, DownloadResult
from localreel.domain.value_objects import SourceMetadata


class YtDlpDownloader(AbstractDownloader):
    _BULK_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "formats",
            "thumbnails",
            "automatic_captions",
            "subtitles",
            "heatmap",
            "requested_formats",
            "requested_downloads",
            "_format_sort_fields",
        }
    )

    def __init__(self, downloads_dir: Path) -> None:
        self._downloads_dir = downloads_dir

    def download(self, *, url: str, video_id: UUID) -> DownloadResult:
        with YoutubeDL(self._options(video_id)) as ydl:
            info = ydl.sanitize_info(ydl.extract_info(url, download=True))
        return self._result(info)

    def discard(self, *, video_id: UUID) -> None:
        for path in self._downloads_dir.glob(f"{video_id}.*"):
            path.unlink(missing_ok=True)

    def _options(self, video_id: UUID) -> dict[str, Any]:
        return {
            "outtmpl": str(self._downloads_dir / f"{video_id}.%(ext)s"),
            "writethumbnail": True,
            "allowed_extractors": [
                "youtube.*",
                "tiktok.*",
                r"vm\.tiktok",
                "facebook.*",
            ],
            # The yt-dlp command's defaults; as a library it retries nothing.
            "retries": 10,
            "fragment_retries": 10,
            "quiet": True,
            "noprogress": True,
        }

    def _result(self, info: dict[str, Any]) -> DownloadResult:
        thumbnails = [
            t["filepath"] for t in info.get("thumbnails", []) if t.get("filepath")
        ]
        duration = info.get("duration")
        return DownloadResult(
            file_path=self._relative(info["requested_downloads"][0]["filepath"]),
            thumbnail_path=self._relative(thumbnails[-1]) if thumbnails else None,
            metadata=SourceMetadata(
                title=info.get("title"),
                description=info.get("description"),
                uploader=info.get("uploader"),
                view_count=info.get("view_count"),
                duration_sec=round(duration) if duration is not None else None,
                width=info.get("width"),
                height=info.get("height"),
                raw={k: v for k, v in info.items() if k not in self._BULK_KEYS},
            ),
        )

    def _relative(self, path: str) -> str:
        return str(Path(path).resolve().relative_to(self._downloads_dir.resolve()))
