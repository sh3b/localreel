import subprocess
import time
from pathlib import Path
from typing import Any
from uuid import uuid7

import pytest

from localreel.adapters.transcoder import FfmpegTranscoder

TIMEOUT_SEC = 60.0
PROBED = '{"streams": [{"width": 64, "height": 64}], "format": {"duration": "1"}}'


class TestTranscodeDeadline:
    def test_each_call_gets_only_the_time_left(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        timeouts: list[float] = []

        def run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
            timeouts.append(kwargs["timeout"])
            time.sleep(0.01)
            stdout = PROBED if "json" in args else "vp9"
            return subprocess.CompletedProcess(args, 0, stdout=stdout)

        monkeypatch.setattr(subprocess, "run", run)

        FfmpegTranscoder(str(tmp_path / "media"), TIMEOUT_SEC).transcode(
            video_id=uuid7(), original_path=str(tmp_path / "src.webm")
        )

        assert len(timeouts) == 5
        assert timeouts[0] <= TIMEOUT_SEC
        assert timeouts == sorted(timeouts, reverse=True)
        assert timeouts[-1] < TIMEOUT_SEC - 0.04
