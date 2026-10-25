import multiprocessing
import os
import signal
from datetime import UTC, datetime
from multiprocessing.connection import Connection
from multiprocessing.process import BaseProcess
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


# Spawn, not fork: the worker has a database pool and threads a forked child
# would inherit.
_PROCESSES = multiprocessing.get_context("spawn")


class YtDlpDownloader(AbstractDownloader):
    def __init__(self, downloads_dir: str, timeout_sec: float) -> None:
        self._downloads_dir = downloads_dir
        self._timeout_sec = timeout_sec

    def download(self, *, url: str, video_id: UUID) -> DownloadResult:
        """Run yt-dlp in a child process, killed at the deadline.

        yt-dlp only gives up after a stretch of network silence, so a download
        that trickles, or the ffmpeg merge it runs afterwards, would otherwise
        hold the worker forever. A thread can't be stopped; a process can.
        """
        receiver, sender = _PROCESSES.Pipe(duplex=False)
        child = _PROCESSES.Process(
            target=self._download_in_child, args=(url, video_id, sender)
        )
        child.start()
        sender.close()
        try:
            if not receiver.poll(self._timeout_sec):
                raise TimeoutError(f"download exceeded {self._timeout_sec:g} s")
            outcome: DownloadResult | str = receiver.recv()
        except EOFError:
            # The child died without a word (OOM kill, crash); its ffmpeg may not.
            self._kill(child)
            raise RuntimeError(
                f"download process exited with code {child.exitcode}"
            ) from None
        except BaseException:
            # Also on SIGTERM and Ctrl-C, which the child, in its own process
            # group, doesn't receive.
            self._kill(child)
            raise
        finally:
            receiver.close()
        child.join()
        if isinstance(outcome, str):
            raise RuntimeError(outcome)
        return outcome

    def _download_in_child(self, url: str, video_id: UUID, sender: Connection) -> None:
        # Its own process group, so the ffmpeg yt-dlp spawns dies with it.
        os.setpgrp()
        try:
            sender.send(self._download(url, video_id))
        except Exception as exc:
            # yt-dlp's errors don't all pickle; the message is what's kept.
            sender.send(str(exc))

    @staticmethod
    def _kill(child: BaseProcess) -> None:
        # is_alive() also reaps a child that has exited: macOS refuses killpg
        # on a group whose leader is an unreaped zombie.
        alive = child.is_alive()
        if child.pid is not None:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                # Nothing left in the group, or killed before it made one.
                if alive:
                    child.kill()
        child.join()

    def _download(self, url: str, video_id: UUID) -> DownloadResult:
        with YoutubeDL(self._options(video_id)) as ydl:
            info = ydl.extract_info(url, download=True)
            info = ydl.sanitize_info(info)

        filepath = str(info["requested_downloads"][0]["filepath"])
        relative = os.path.relpath(filepath, self._downloads_dir)
        return DownloadResult(
            original_path=relative,
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
            # No generic extractor: it fetches any URL, internal ones included.
            # vm.tiktok handles TikTok's vm./vt. short links.
            "allowed_extractors": [
                "youtube.*",
                "tiktok.*",
                r"vm\.tiktok",
                "facebook.*",
            ],
            "quiet": True,
            "noprogress": True,
        }
