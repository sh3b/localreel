import shutil
import subprocess
from pathlib import Path
from uuid import uuid7

import pytest

from localreel.adapters.transcoder import FfmpegTranscoder

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="needs ffmpeg and ffprobe on PATH",
)

TIMEOUT_SEC = 60.0


def _codec(path: Path, stream: str) -> str:
    result = subprocess.run(
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
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _make_source(path: Path, *, video: list[str], audio: list[str]) -> Path:
    """Synthesise a tiny clip so no binary fixtures live in the repo."""
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=1:size=64x64:rate=10",
            "-f",
            "lavfi",
            "-i",
            "sine=duration=1",
            *video,
            *audio,
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    return path


@pytest.fixture
def media_dir(tmp_path: Path) -> Path:
    return tmp_path / "media"


class TestFfmpegTranscoder:
    def test_h264_aac_source_is_copied_not_reencoded(
        self, tmp_path: Path, media_dir: Path
    ) -> None:
        source = _make_source(
            tmp_path / "src.mp4",
            video=["-c:v", "libx264", "-pix_fmt", "yuv420p"],
            audio=["-c:a", "aac"],
        )
        video_id = uuid7()

        result = FfmpegTranscoder(str(media_dir), TIMEOUT_SEC).transcode(
            video_id=video_id, original_path=str(source)
        )

        playback = Path(result.playback_path)
        assert playback == media_dir / str(video_id) / f"{video_id}.mp4"
        assert playback.exists()
        assert _codec(playback, "v:0") == "h264"
        assert _codec(playback, "a:0") == "aac"

    def test_vp9_opus_source_is_reencoded_to_h264_aac(
        self, tmp_path: Path, media_dir: Path
    ) -> None:
        source = _make_source(
            tmp_path / "src.webm",
            video=["-c:v", "libvpx-vp9", "-deadline", "realtime", "-cpu-used", "8"],
            audio=["-c:a", "libopus"],
        )

        result = FfmpegTranscoder(str(media_dir), TIMEOUT_SEC).transcode(
            video_id=uuid7(), original_path=str(source)
        )

        playback = Path(result.playback_path)
        assert _codec(playback, "v:0") == "h264"
        assert _codec(playback, "a:0") == "aac"

    def test_h264_opus_source_reencodes_audio_only(
        self, tmp_path: Path, media_dir: Path
    ) -> None:
        source = _make_source(
            tmp_path / "src.mkv",
            video=["-c:v", "libx264", "-pix_fmt", "yuv420p"],
            audio=["-c:a", "libopus"],
        )

        result = FfmpegTranscoder(str(media_dir), TIMEOUT_SEC).transcode(
            video_id=uuid7(), original_path=str(source)
        )

        playback = Path(result.playback_path)
        assert _codec(playback, "v:0") == "h264"
        assert _codec(playback, "a:0") == "aac"

    def test_generates_a_thumbnail_when_there_is_no_source_image(
        self, tmp_path: Path, media_dir: Path
    ) -> None:
        source = _make_source(
            tmp_path / "src.mp4",
            video=["-c:v", "libx264", "-pix_fmt", "yuv420p"],
            audio=["-c:a", "aac"],
        )
        video_id = uuid7()

        result = FfmpegTranscoder(str(media_dir), TIMEOUT_SEC).transcode(
            video_id=video_id, original_path=str(source)
        )

        thumbnail = Path(result.thumbnail_path)
        assert thumbnail == media_dir / str(video_id) / f"{video_id}-thumbnail.jpg"
        assert _codec(thumbnail, "v:0") == "mjpeg"

    def test_prefers_the_archived_source_thumbnail(
        self, tmp_path: Path, media_dir: Path
    ) -> None:
        video_id = uuid7()
        source = _make_source(
            tmp_path / f"{video_id}.mp4",
            video=["-c:v", "libx264", "-pix_fmt", "yuv420p"],
            audio=["-c:a", "aac"],
        )
        archived = tmp_path / f"{video_id}-thumbnail.jpg"
        archived.write_bytes(b"not really a jpeg")

        result = FfmpegTranscoder(str(media_dir), TIMEOUT_SEC).transcode(
            video_id=video_id, original_path=str(source)
        )

        # Copied verbatim rather than regenerated from a frame.
        assert Path(result.thumbnail_path).read_bytes() == b"not really a jpeg"

    def test_leaves_no_staging_directory_behind(
        self, tmp_path: Path, media_dir: Path
    ) -> None:
        source = _make_source(
            tmp_path / "src.mp4",
            video=["-c:v", "libx264", "-pix_fmt", "yuv420p"],
            audio=["-c:a", "aac"],
        )
        video_id = uuid7()

        FfmpegTranscoder(str(media_dir), TIMEOUT_SEC).transcode(
            video_id=video_id, original_path=str(source)
        )

        assert [p.name for p in media_dir.iterdir()] == [str(video_id)]

    def test_failure_surfaces_as_an_exception(
        self, tmp_path: Path, media_dir: Path
    ) -> None:
        broken = tmp_path / "broken.mp4"
        broken.write_bytes(b"not a video")

        with pytest.raises(subprocess.CalledProcessError):
            FfmpegTranscoder(str(media_dir), TIMEOUT_SEC).transcode(
                video_id=uuid7(), original_path=str(broken)
            )
