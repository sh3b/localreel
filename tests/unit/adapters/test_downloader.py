from pathlib import Path
from typing import Any, ClassVar
from uuid import uuid7

import pytest
from yt_dlp import YoutubeDL
from yt_dlp.options import create_parser
from yt_dlp.utils import DownloadError, ExtractorError

from localreel.adapters.downloader import YtDlpDownloader
from localreel.domain.downloader import DownloadResult
from localreel.domain.exceptions import DownloadFailed


def _raise(error: Exception) -> Any:
    def extract_info(*_: Any, **__: Any) -> Any:
        raise error

    return extract_info


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

    def test_retries_like_the_yt_dlp_command(self) -> None:
        options = YtDlpDownloader(Path("/downloads"))._options(uuid7())
        command_defaults = create_parser().defaults

        assert options["retries"] == command_defaults["retries"]
        assert options["fragment_retries"] == command_defaults["fragment_retries"]

    def test_refuses_a_url_no_allowed_extractor_handles(self, tmp_path: Path) -> None:
        with pytest.raises(DownloadFailed, match="No suitable extractor"):
            YtDlpDownloader(tmp_path).download(
                url="http://169.254.169.254/latest/meta-data", video_id=uuid7()
            )

    def _refused(
        self, cause: ExtractorError, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> str:
        error = DownloadError(f"ERROR: {cause}", exc_info=(type(cause), cause, None))
        monkeypatch.setattr(YoutubeDL, "extract_info", _raise(error))
        with pytest.raises(DownloadFailed) as raised:
            YtDlpDownloader(tmp_path).download(
                url="https://youtu.be/xxxxxxxxxx0", video_id=uuid7()
            )
        return str(raised.value)

    def test_a_refusal_keeps_the_site_and_its_id(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cause = ExtractorError(
            "This video is unavailable",
            expected=True,
            video_id="xxxxxxxxxx0",
            ie="youtube",
        )

        reason = self._refused(cause, tmp_path, monkeypatch)

        assert reason == "[youtube] xxxxxxxxxx0: This video is unavailable"

    def test_a_refusal_yt_dlp_did_not_expect_leaves_out_its_bug_report_advice(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cause = ExtractorError("Cannot parse data", video_id="1", ie="facebook")
        assert "please report this issue" in str(cause)

        reason = self._refused(cause, tmp_path, monkeypatch)

        assert reason == "[facebook] 1: Cannot parse data"

    def test_a_refusal_keeps_what_caused_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cause = ExtractorError(
            "Unable to download webpage",
            expected=True,
            cause=ConnectionResetError("reset by peer"),
            video_id="xxxxxxxxxx0",
            ie="youtube",
        )

        reason = self._refused(cause, tmp_path, monkeypatch)

        assert reason == (
            "[youtube] xxxxxxxxxx0: Unable to download webpage"
            " (caused by ConnectionResetError('reset by peer'))"
        )

    def test_a_refusal_without_site_or_id_gives_the_reason_alone(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cause = ExtractorError("Requested format is not available", expected=True)

        reason = self._refused(cause, tmp_path, monkeypatch)

        assert reason == "Requested format is not available"

    def test_a_failed_download_gives_the_message_without_error_prefix(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        error = DownloadError(
            "ERROR: unable to download video data: HTTP Error 403: Forbidden"
        )
        monkeypatch.setattr(YoutubeDL, "extract_info", _raise(error))

        with pytest.raises(DownloadFailed) as raised:
            YtDlpDownloader(tmp_path).download(
                url="https://youtu.be/jNQXAC9IVRw", video_id=uuid7()
            )

        assert str(raised.value) == (
            "unable to download video data: HTTP Error 403: Forbidden"
        )

    def test_discard_deletes_every_file_of_the_video_and_only_those(
        self, tmp_path: Path
    ) -> None:
        video_id, other_id = uuid7(), uuid7()
        for name in (
            f"{video_id}.f401.mp4.part",
            f"{video_id}.f251.webm",
            f"{video_id}.webm.ytdl",
            f"{video_id}.webp",
            f"{other_id}.webm",
        ):
            (tmp_path / name).touch()

        YtDlpDownloader(tmp_path).discard(video_id=video_id)

        assert [path.name for path in tmp_path.iterdir()] == [f"{other_id}.webm"]

    def test_discard_without_files_does_nothing(self, tmp_path: Path) -> None:
        YtDlpDownloader(tmp_path).discard(video_id=uuid7())

        assert list(tmp_path.iterdir()) == []


class TestDownloadResult:
    INFO: ClassVar[dict[str, Any]] = {
        "id": "jNQXAC9IVRw",
        "extractor": "youtube",
        "title": "Me at the zoo",
        "description": "The first video on YouTube.",
        "uploader": "jawed",
        "view_count": 448473011,
        "duration": 19.4,
        "width": 320,
        "height": 240,
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
        assert (metadata.width, metadata.height) == (320, 240)

    def test_raw_keeps_everything_but_the_bulky_keys(self) -> None:
        raw = self._result().metadata.raw

        assert raw["id"] == "jNQXAC9IVRw"
        assert raw["extractor"] == "youtube"
        assert "formats" not in raw
        assert "thumbnails" not in raw
        assert "automatic_captions" not in raw
        assert "requested_downloads" not in raw

    def test_uploader_url_is_the_one_yt_dlp_gave(self) -> None:
        result = self._result(
            uploader_url="https://www.youtube.com/@jawed",
            channel_url="https://www.youtube.com/channel/UC4QobU6",
        )

        assert result.metadata.uploader_url == "https://www.youtube.com/@jawed"

    def test_uploader_url_falls_back_to_the_channel_url(self) -> None:
        result = self._result(channel_url="https://www.youtube.com/channel/UC4QobU6")

        assert result.metadata.uploader_url == (
            "https://www.youtube.com/channel/UC4QobU6"
        )

    def test_a_facebook_uploader_is_linked_by_their_id(self) -> None:
        result = self._result(extractor_key="Facebook", uploader_id="61575450508225")

        assert result.metadata.uploader_url == "https://www.facebook.com/61575450508225"

    def test_empty_links_from_yt_dlp_count_as_none(self) -> None:
        result = self._result(
            extractor_key="Facebook",
            uploader_url="",
            channel_url="",
            uploader_id="61575450508225",
        )

        assert result.metadata.uploader_url == "https://www.facebook.com/61575450508225"

    def test_other_sites_get_no_link_from_an_id(self) -> None:
        result = self._result(extractor_key="Youtube", uploader_id="61575450508225")

        assert result.metadata.uploader_url is None

    def test_tolerates_missing_fields(self) -> None:
        info = {
            "id": "x",
            "requested_downloads": [{"filepath": "/downloads/v.mp4"}],
        }

        result = YtDlpDownloader(Path("/downloads"))._result(info)

        assert result.metadata.title is None
        assert result.metadata.uploader_url is None
        assert result.metadata.duration_sec is None
        assert (result.metadata.width, result.metadata.height) == (None, None)
        assert result.thumbnail_path is None
