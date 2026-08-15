from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from localreel.adapters.downloader import YtDlpDownloader
from localreel.domain.value_objects.source_metadata import SourceMetadata

VIDEO_ID = UUID("0198f0a0-0000-7000-8000-000000000001")

INFO: dict[str, Any] = {
    "id": "aBcDeFgHiJk",
    "extractor": "youtube",
    "title": "A Short Title",
    "description": "",
    "uploader": "A Channel",
    "uploader_id": "@achannel",
    "channel": "A Channel",
    "channel_id": "UC00000000000000000001",
    "timestamp": 1748357838,
    "view_count": 42984,
    "formats": [{"format_id": "18"}],
    "automatic_captions": {"en": []},
    "thumbnails": [{"url": "https://example.test/t.jpg"}],
    "requested_downloads": [{"filepath": "/downloads/x.mp4"}],
}


class TestSourceMetadataMapping:
    def _metadata(self, **overrides: Any) -> SourceMetadata:
        return YtDlpDownloader("/downloads")._source_metadata({**INFO, **overrides})

    def test_maps_the_portable_fields(self) -> None:
        metadata = self._metadata()

        assert metadata.source_id == "aBcDeFgHiJk"
        assert metadata.title == "A Short Title"
        assert metadata.uploader == "A Channel"
        assert metadata.uploader_id == "@achannel"
        assert metadata.view_count == 42984

    def test_converts_timestamp_to_an_aware_datetime(self) -> None:
        assert self._metadata().published_at == datetime(
            2025, 5, 27, 14, 57, 18, tzinfo=UTC
        )

    def test_tolerates_a_missing_timestamp(self) -> None:
        assert self._metadata(timestamp=None).published_at is None

    def test_keeps_an_empty_description_rather_than_nulling_it(self) -> None:
        assert self._metadata().description == ""

    def test_strips_bulk_keys_from_raw(self) -> None:
        raw = self._metadata().raw

        assert "automatic_captions" not in raw
        assert "formats" not in raw
        assert "thumbnails" not in raw
        assert "requested_downloads" not in raw

    def test_keeps_youtube_only_extras_in_raw(self) -> None:
        raw = self._metadata().raw

        assert raw["channel_id"] == "UC00000000000000000001"
        assert raw["extractor"] == "youtube"

    def test_coerces_a_numeric_id_to_text(self) -> None:
        assert self._metadata(id=10000000000000001).source_id == "10000000000000001"


class TestYtDlpDownloaderOptions:
    def _options(self) -> dict[str, Any]:
        return YtDlpDownloader("/downloads")._options(VIDEO_ID)

    def test_requests_best_video_and_audio_merged(self) -> None:
        assert self._options()["format"] == "bestvideo*+bestaudio/best"

    def test_writes_the_mezzanine_into_downloads_dir(self) -> None:
        assert self._options()["outtmpl"]["default"] == f"/downloads/{VIDEO_ID}.%(ext)s"

    def test_archives_the_thumbnail_beside_the_mezzanine(self) -> None:
        options = self._options()

        assert options["writethumbnail"] is True
        assert (
            options["outtmpl"]["thumbnail"]
            == f"/downloads/{VIDEO_ID}-thumbnail.%(ext)s"
        )

    def test_converts_the_thumbnail_to_jpg(self) -> None:
        assert self._options()["postprocessors"] == [
            {"key": "FFmpegThumbnailsConvertor", "format": "jpg", "when": "before_dl"}
        ]
