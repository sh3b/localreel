from pathlib import Path
from uuid import uuid7

import pytest
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from localreel.adapters.downloader import YtDlpDownloader


class TestYtDlpDownloader:
    def test_names_the_file_after_the_video_id(self) -> None:
        video_id = uuid7()

        options = YtDlpDownloader(Path("/downloads"))._options(video_id)

        assert options["outtmpl"] == f"/downloads/{video_id}.%(ext)s"

    def test_loads_only_supported_site_extractors(self) -> None:
        allowed = YtDlpDownloader(Path("/downloads"))._options(uuid7())[
            "allowed_extractors"
        ]

        with YoutubeDL({"allowed_extractors": allowed, "quiet": True}) as ydl:
            loaded = {key.lower() for key in ydl._ies}

        assert "generic" not in loaded
        assert {"youtube", "tiktok", "tiktokvm", "facebook"} <= loaded

    def test_refuses_a_url_no_allowed_extractor_handles(self, tmp_path: Path) -> None:
        with pytest.raises(DownloadError, match="No suitable extractor"):
            YtDlpDownloader(tmp_path).download(
                url="http://169.254.169.254/latest/meta-data", video_id=uuid7()
            )
