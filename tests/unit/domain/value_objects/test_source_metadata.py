from datetime import UTC, datetime

from tests.factories.video import VideoFactory

from localreel.domain.types import VideoSource
from localreel.domain.value_objects.source_metadata import SourceMetadata

METADATA = SourceMetadata(
    source_id="aBcDeFgHiJk",
    title="A Short Title",
    description="",
    uploader="A Channel",
    uploader_id="@achannel",
    published_at=datetime(2025, 5, 27, 14, 57, 18, tzinfo=UTC),
    view_count=42984,
    raw={"id": "aBcDeFgHiJk", "extractor": "youtube"},
)


class TestSourceMetadataOnVideo:
    def test_absent_until_downloaded(self) -> None:
        assert VideoFactory().source_metadata is None

    def test_round_trips_through_the_flat_columns(self) -> None:
        video = VideoFactory()
        video.mark_downloading()

        video.mark_downloaded("/downloads/x.webm", METADATA)

        assert video.source_metadata == METADATA
        assert video.source_title == "A Short Title"
        assert video.source_view_count == 42984

    def test_local_uploads_keep_no_source_layer(self) -> None:
        video = VideoFactory(source=VideoSource.LOCAL)

        video.mark_downloaded("/uploads/x.mp4")

        assert video.source_metadata is None
        assert video.source_id is None

    def test_an_empty_description_is_not_a_missing_one(self) -> None:
        video = VideoFactory()
        video.mark_downloading()

        video.mark_downloaded("/downloads/x.webm", METADATA)

        assert video.source_metadata is not None
        assert video.source_metadata.description == ""
