import json
import os
import shutil
import subprocess
from pathlib import Path
from uuid import UUID

from localreel.domain.abstractions.transcoder import (
    AbstractTranscoder,
    TranscodeResult,
)

BROWSER_SAFE_VIDEO = "h264"
BROWSER_SAFE_AUDIO = "aac"


class FfmpegTranscoder(AbstractTranscoder):
    def __init__(self, media_dir: str, timeout_sec: float) -> None:
        self._media_dir = Path(media_dir)
        self._timeout_sec = timeout_sec

    def transcode(self, *, video_id: UUID, original_path: str) -> TranscodeResult:
        out_dir = self._media_dir / str(video_id)
        # Build into a staging directory and swap it in at the end, so a crash
        # never leaves a truncated mp4 where a serving layer would find it.
        staging = self._media_dir / f".{video_id}.tmp"
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True)

        self._write_playback(original_path, staging / f"{video_id}.mp4")
        self._write_thumbnail(
            video_id, original_path, staging / f"{video_id}-thumbnail.jpg"
        )

        shutil.rmtree(out_dir, ignore_errors=True)
        os.replace(staging, out_dir)

        duration_sec, width, height = self._probe_media(original_path)
        return TranscodeResult(
            playback_path=str(out_dir / f"{video_id}.mp4"),
            thumbnail_path=str(out_dir / f"{video_id}-thumbnail.jpg"),
            duration_sec=duration_sec,
            width=width,
            height=height,
        )

    def _probe_media(self, path: str) -> tuple[int | None, int | None, int | None]:
        """Read from the file, not yt-dlp, so LOCAL uploads work the same."""
        result = self._run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height:format=duration",
                "-of",
                "json",
                path,
            ]
        )
        probed = json.loads(result.stdout)
        stream = (probed.get("streams") or [{}])[0]
        duration = probed.get("format", {}).get("duration")
        return (
            # Sources report fractional seconds (77.855); the column is integer.
            round(float(duration)) if duration is not None else None,
            stream.get("width"),
            stream.get("height"),
        )

    def _write_playback(self, original_path: str, destination: Path) -> None:
        video_codec = self._probe_codec(original_path, "v:0")
        audio_codec = self._probe_codec(original_path, "a:0")

        if video_codec == BROWSER_SAFE_VIDEO and audio_codec in (
            BROWSER_SAFE_AUDIO,
            None,
        ):
            # Already playable: rewrap only. Seconds, and bit-for-bit identical.
            codec_args = ["-c", "copy"]
        elif video_codec == BROWSER_SAFE_VIDEO:
            # Video is where the CPU goes, so re-encode audio alone.
            codec_args = ["-c:v", "copy", "-c:a", "aac"]
        else:
            # yuv420p because browsers expecting 4:2:0 render 4:2:2/10-bit
            # sources as a black screen rather than failing loudly.
            codec_args = [
                "-c:v",
                "libx264",
                "-crf",
                "20",
                "-preset",
                "medium",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
            ]

        # +faststart moves the moov index to the front; without it the browser
        # must download the whole file before it can play or seek.
        self._run(
            [
                "ffmpeg",
                "-y",
                "-i",
                original_path,
                *codec_args,
                "-movflags",
                "+faststart",
                str(destination),
            ]
        )

    def _write_thumbnail(
        self, video_id: UUID, original_path: str, destination: Path
    ) -> None:
        # The downloader archives the source image beside the mezzanine for
        # remote videos. LOCAL uploads have none, so fall back to a frame.
        source = Path(original_path).with_name(f"{video_id}-thumbnail.jpg")
        if source.exists():
            shutil.copyfile(source, destination)
            return

        # The thumbnail filter picks the most representative frame of those it
        # analyses, which avoids the black frame a fixed offset lands on when a
        # clip fades in.
        self._run(
            [
                "ffmpeg",
                "-y",
                "-i",
                original_path,
                "-vf",
                "thumbnail",
                "-frames:v",
                "1",
                str(destination),
            ]
        )

    def _probe_codec(self, path: str, stream: str) -> str | None:
        result = self._run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                stream,
                "-show_entries",
                "stream=codec_name",
                "-of",
                "csv=p=0",
                path,
            ]
        )
        return result.stdout.strip() or None

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args,
            check=True,
            capture_output=True,
            text=True,
            timeout=self._timeout_sec,
        )
