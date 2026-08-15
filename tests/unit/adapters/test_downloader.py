from pathlib import Path
from typing import Any, ClassVar
from uuid import uuid7

import pytest
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from localreel.adapters.downloader import YtDlpDownloader
from localreel.domain.downloader import DownloadResult


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


class TestDownloadResult:
    INFO: ClassVar[dict[str, Any]] = {
        "id": "jNQXAC9IVRw",
        "extractor": "youtube",
        "title": "Me at the zoo",
        "description": "The first video on YouTube.",
        "uploader": "jawed",
        "view_count": 448473011,
        "duration": 19.4,
        "formats": [{"format_id": "18"}],
        "automatic_captions": {"en": []},
        "thumbnails": [
            {"url": "https://i.ytimg.com/vi/jNQXAC9IVRw/1.jpg"},
            {
                "url": "https://i.ytimg.com/vi/jNQXAC9IVRw/2.webp",
                "filepath": "/downloads/v.webp",
            },
        ],
        "requested_downloads": [{"filepath": "/downloads/v.webm"}],
    }

    def _result(self, **overrides: Any) -> DownloadResult:
        return YtDlpDownloader(Path("/downloads"))._result({**self.INFO, **overrides})

    def test_paths_are_relative_to_the_downloads_dir(self) -> None:
        result = self._result()

        assert result.file_path == "v.webm"
        assert result.thumbnail_path == "v.webp"

    def test_thumbnail_is_none_when_none_was_written(self) -> None:
        result = self._result(thumbnails=[{"url": "https://i.ytimg.com/1.jpg"}])

        assert result.thumbnail_path is None

    def test_maps_the_metadata(self) -> None:
        metadata = self._result().metadata

        assert metadata.title == "Me at the zoo"
        assert metadata.description == "The first video on YouTube."
        assert metadata.uploader == "jawed"
        assert metadata.view_count == 448473011
        assert metadata.duration_sec == 19

    def test_raw_keeps_everything_but_the_bulky_keys(self) -> None:
        raw = self._result().metadata.raw

        assert raw["id"] == "jNQXAC9IVRw"
        assert raw["extractor"] == "youtube"
        assert "formats" not in raw
        assert "thumbnails" not in raw
        assert "automatic_captions" not in raw
        assert "requested_downloads" not in raw

    def test_tolerates_missing_fields(self) -> None:
        info = {
            "id": "x",
            "requested_downloads": [{"filepath": "/downloads/v.mp4"}],
        }

        result = YtDlpDownloader(Path("/downloads"))._result(info)

        assert result.metadata.title is None
        assert result.metadata.duration_sec is None
        assert result.thumbnail_path is None
