from pathlib import Path
from typing import Any, ClassVar
from uuid import UUID

from localreel.domain.downloader import AbstractDownloader, DownloadResult
from localreel.domain.exceptions import DownloadFailed
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
        # Imported here: yt-dlp takes about 50 MB, and the API, which never
        # downloads, imports this module too (containers.py).
        from yt_dlp import YoutubeDL
        from yt_dlp.utils import DownloadError, ExtractorError

        with YoutubeDL(self._options(video_id)) as ydl:
            try:
                info = ydl.sanitize_info(ydl.extract_info(url, download=True))
            except DownloadError as exc:
                # yt-dlp's message reads "ERROR: [facebook] <id>: <reason>
                # (caused by ...)", plus, for an error yt-dlp didn't expect,
                # advice to report it as a bug. The reason keeps all of it but
                # that advice.
                reason = str(exc).removeprefix("ERROR: ")
                cause = exc.exc_info[1] if exc.exc_info else None
                if isinstance(cause, ExtractorError):
                    reason = cause.orig_msg
                    if cause.video_id:
                        reason = f"{cause.video_id}: {reason}"
                    if cause.ie:
                        reason = f"[{cause.ie}] {reason}"
                    if cause.cause:
                        reason = f"{reason} (caused by {cause.cause!r})"
                raise DownloadFailed(reason) from exc
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
        # yt-dlp gives an empty string for a field the site left blank (an
        # empty description, say); every text field saves it as None instead,
        # so a missing value is always NULL. Facebook gives only the
        # uploader's numeric id; facebook.com/<id> redirects to their page.
        uploader_url = info.get("uploader_url") or info.get("channel_url") or None
        uploader_id = info.get("uploader_id")
        if uploader_url is None and info.get("extractor_key") == "Facebook":
            if uploader_id:
                uploader_url = f"https://www.facebook.com/{uploader_id}"
        return DownloadResult(
            file_path=self._relative(info["requested_downloads"][0]["filepath"]),
            thumbnail_path=self._relative(thumbnails[-1]) if thumbnails else None,
            metadata=SourceMetadata(
                title=info.get("title") or None,
                description=info.get("description") or None,
                uploader=info.get("uploader") or None,
                uploader_url=uploader_url,
                view_count=info.get("view_count"),
                duration_sec=round(duration) if duration is not None else None,
                width=info.get("width"),
                height=info.get("height"),
                raw={k: v for k, v in info.items() if k not in self._BULK_KEYS},
            ),
        )

    def _relative(self, path: str) -> str:
        return str(Path(path).resolve().relative_to(self._downloads_dir.resolve()))
