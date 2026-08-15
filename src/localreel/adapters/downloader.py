from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from yt_dlp import YoutubeDL

from localreel.domain.abstractions.downloader import AbstractDownloader, DownloadResult
from localreel.domain.value_objects.source_metadata import SourceMetadata

BULK_KEYS = frozenset(
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


class YtDlpDownloader(AbstractDownloader):
    def __init__(self, downloads_dir: str) -> None:
        self._downloads_dir = downloads_dir

    def download(self, *, url: str, video_id: UUID) -> DownloadResult:
        with YoutubeDL(self._options(video_id)) as ydl:
            info = ydl.extract_info(url, download=True)
            info = ydl.sanitize_info(info)

        return DownloadResult(
            # `requested_downloads[0].filepath` is the final path after any
            # merge/postprocessing, unlike prepare_filename() which predates it.
            original_path=str(info["requested_downloads"][0]["filepath"]),
            source_metadata=self._source_metadata(info),
        )

    @staticmethod
    def _source_metadata(info: dict[str, Any]) -> SourceMetadata:
        timestamp = info.get("timestamp")
        return SourceMetadata(
            source_id=str(info["id"]),
            title=info.get("title"),
            description=info.get("description"),
            # Not channel/channel_id: those are YouTube-only, absent on Facebook.
            uploader=info.get("uploader"),
            uploader_id=info.get("uploader_id"),
            published_at=(
                datetime.fromtimestamp(timestamp, UTC) if timestamp else None
            ),
            view_count=info.get("view_count"),
            raw={k: v for k, v in info.items() if k not in BULK_KEYS},
        )

    def _options(self, video_id: UUID) -> dict[str, Any]:
        return {
            # Explicit because the default silently degrades to a muxed 360p
            # format when ffmpeg isn't there to merge the streams.
            "format": "bestvideo*+bestaudio/best",
            "outtmpl": {
                "default": f"{self._downloads_dir}/{video_id}.%(ext)s",
                # Not media_dir: transcode owns that tree and must be able to
                # rebuild it without a re-download.
                "thumbnail": f"{self._downloads_dir}/{video_id}-thumbnail.%(ext)s",
            },
            "writethumbnail": True,
            # Sites serve webp/avif; transcode looks for a .jpg.
            "postprocessors": [
                {
                    "key": "FFmpegThumbnailsConvertor",
                    "format": "jpg",
                    "when": "before_dl",
                }
            ],
            "quiet": True,
            "noprogress": True,
        }
