"""Guards the filename convention the downloader and transcoder share.

Each side is otherwise tested against its own literal, so a rename on one leaves
every test green and silently degrades to a frame grab.
"""

import shutil
import subprocess
from pathlib import Path
from uuid import uuid7

import pytest

from localreel.adapters.downloader import YtDlpDownloader
from localreel.adapters.transcoder import FfmpegTranscoder

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="needs ffmpeg and ffprobe on PATH",
)

TIMEOUT_SEC = 60.0
ARCHIVED_IMAGE = b"not really a jpeg"


class TestSourceThumbnailHandoff:
    def test_transcode_finds_what_the_downloader_archives(self, tmp_path: Path) -> None:
        downloads_dir = tmp_path / "downloads"
        downloads_dir.mkdir()
        video_id = uuid7()
        options = YtDlpDownloader(str(downloads_dir))._options(video_id)

        assert options["postprocessors"][0]["format"] == "jpg"
        mezzanine = Path(options["outtmpl"]["default"] % {"ext": "mp4"})
        archived = Path(options["outtmpl"]["thumbnail"] % {"ext": "jpg"})

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc=duration=1:size=64x64:rate=10",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(mezzanine),
            ],
            check=True,
            capture_output=True,
        )
        archived.write_bytes(ARCHIVED_IMAGE)

        result = FfmpegTranscoder(str(tmp_path / "media"), TIMEOUT_SEC).transcode(
            video_id=video_id, original_path=str(mezzanine)
        )

        media_dir = tmp_path / "media"
        assert (media_dir / result.thumbnail_path).read_bytes() == ARCHIVED_IMAGE
