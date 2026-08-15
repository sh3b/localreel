from datetime import UTC, datetime
from uuid import UUID

from localreel.containers import Container
from localreel.domain.abstractions.downloader import AbstractDownloader, DownloadResult
from localreel.domain.types import VideoStatus
from localreel.domain.value_objects.source_metadata import SourceMetadata
from localreel.service_layer.download import download_next_pending
from tests.factories.video import VideoFactory

_METADATA = SourceMetadata(
    source_id="aBcDeFgHiJk",
    title="A Short Title",
    description="",
    uploader="A Channel",
    uploader_id="@achannel",
    published_at=datetime(2025, 5, 27, 14, 57, 18, tzinfo=UTC),
    view_count=42984,
    raw={"id": "aBcDeFgHiJk", "extractor": "youtube"},
)
_RESULT = DownloadResult(original_path="/data/x.mp4", source_metadata=_METADATA)


class _FakeDownloader(AbstractDownloader):
    def __init__(
        self, *, result: DownloadResult | None = None, error: Exception | None = None
    ):
        self._result = result
        self._error = error

    def download(self, *, url: str, video_id: UUID) -> DownloadResult:
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


class TestDownloadNextPending:
    def test_claims_downloads_and_marks_downloaded(self, container: Container) -> None:
        uow = container.uow()
        with uow:
            video = VideoFactory()
            uow.videos.add(video)
            video_id = video.id

        did_work = download_next_pending(
            uow, container.message_bus(), _FakeDownloader(result=_RESULT)
        )

        assert did_work is True
        with uow:
            loaded = uow.videos.get(video_id)
            assert loaded.status is VideoStatus.DOWNLOADED
            assert loaded.original_path == "/data/x.mp4"
            assert loaded.source_metadata == _METADATA
            assert loaded.source_file_available is True

    def test_download_failure_marks_failed(self, container: Container) -> None:
        uow = container.uow()
        with uow:
            video = VideoFactory()
            uow.videos.add(video)
            video_id = video.id

        did_work = download_next_pending(
            uow, container.message_bus(), _FakeDownloader(error=RuntimeError("boom"))
        )

        assert did_work is True
        with uow:
            loaded = uow.videos.get(video_id)
            assert loaded.status is VideoStatus.FAILED
            assert loaded.error_message == "boom"

    def test_returns_false_when_nothing_pending(self, container: Container) -> None:
        uow = container.uow()

        did_work = download_next_pending(
            uow, container.message_bus(), _FakeDownloader(result=_RESULT)
        )

        assert did_work is False
