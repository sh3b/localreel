"""The child process around yt-dlp, with its download replaced by stand-ins."""

import os
import signal
import subprocess
import threading
import time
from pathlib import Path
from uuid import UUID, uuid7

import pytest

from localreel.adapters.downloader import YtDlpDownloader
from localreel.domain.abstractions.downloader import DownloadResult
from localreel.domain.value_objects.source_metadata import SourceMetadata

URL = "https://www.youtube.com/watch?v=aBcDeFgHiJk"
TIMEOUT_SEC = 30

RESULT = DownloadResult(
    original_path="x.mp4",
    source_metadata=SourceMetadata(
        source_id="aBcDeFgHiJk",
        title=None,
        description=None,
        uploader=None,
        uploader_id=None,
        published_at=None,
        view_count=None,
        raw={},
    ),
)


class _Finishes(YtDlpDownloader):
    def _download(self, url: str, video_id: UUID) -> DownloadResult:
        return RESULT


class _Fails(YtDlpDownloader):
    def _download(self, url: str, video_id: UUID) -> DownloadResult:
        raise ValueError("Video unavailable")


class _Dies(YtDlpDownloader):
    def _download(self, url: str, video_id: UUID) -> DownloadResult:
        os._exit(3)


class _HangsInMerge(YtDlpDownloader):
    """Starts a grandchild, as yt-dlp does for the ffmpeg merge, and never returns."""

    def _download(self, url: str, video_id: UUID) -> DownloadResult:
        merge = subprocess.Popen(["sleep", "60"])
        Path(self._downloads_dir, "merge.pid").write_text(str(merge.pid))
        time.sleep(60)
        return RESULT


def _is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def _assert_merge_killed(downloads_dir: Path) -> None:
    pid_file = downloads_dir / "merge.pid"
    assert pid_file.exists(), "the child never started its merge"
    merge_pid = int(pid_file.read_text())
    # The orphaned merge is reaped by init, not instantly.
    give_up = time.monotonic() + 5
    while _is_running(merge_pid) and time.monotonic() < give_up:
        time.sleep(0.05)
    assert not _is_running(merge_pid)


class TestYtDlpDownloaderProcess:
    def test_returns_what_the_child_downloaded(self, tmp_path: Path) -> None:
        downloader = _Finishes(str(tmp_path), TIMEOUT_SEC)

        assert downloader.download(url=URL, video_id=uuid7()) == RESULT

    def test_a_download_error_keeps_its_message(self, tmp_path: Path) -> None:
        downloader = _Fails(str(tmp_path), TIMEOUT_SEC)

        with pytest.raises(RuntimeError, match="Video unavailable"):
            downloader.download(url=URL, video_id=uuid7())

    def test_a_child_that_dies_is_reported(self, tmp_path: Path) -> None:
        downloader = _Dies(str(tmp_path), TIMEOUT_SEC)

        with pytest.raises(RuntimeError, match="exited with code 3"):
            downloader.download(url=URL, video_id=uuid7())

    def test_a_download_past_its_deadline_is_killed_with_its_merge(
        self, tmp_path: Path
    ) -> None:
        downloader = _HangsInMerge(str(tmp_path), 5)

        with pytest.raises(TimeoutError, match="download exceeded 5 s"):
            downloader.download(url=URL, video_id=uuid7())

        _assert_merge_killed(tmp_path)

    def test_ctrl_c_mid_download_kills_the_child_and_its_merge(
        self, tmp_path: Path
    ) -> None:
        downloader = _HangsInMerge(str(tmp_path), TIMEOUT_SEC)
        ctrl_c = threading.Timer(5.0, os.kill, (os.getpid(), signal.SIGINT))
        ctrl_c.start()

        with pytest.raises(KeyboardInterrupt):
            downloader.download(url=URL, video_id=uuid7())

        _assert_merge_killed(tmp_path)
