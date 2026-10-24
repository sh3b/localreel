from datetime import UTC, datetime
from uuid import UUID

import pytest

from localreel.containers import Container
from localreel.domain.abstractions.downloader import AbstractDownloader, DownloadResult
from localreel.domain.commands import MarkFailed
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
# Longer than any test, so no beat fires: a second thread would share the
# test's single connection.
_HEARTBEAT_SEC = 3600.0

_RESULT = DownloadResult(original_path="x.mp4", source_metadata=_METADATA)


class _FakeDownloader(AbstractDownloader):
    def __init__(
        self,
        *,
        result: DownloadResult | None = None,
        error: BaseException | None = None,
    ):
        self._result = result
        self._error = error

    def download(self, *, url: str, video_id: UUID) -> DownloadResult:
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


class _SweptMidDownload(AbstractDownloader):
    """Has the sweep fail the video while the download runs."""

    def __init__(self, container: Container) -> None:
        self._container = container

    def download(self, *, url: str, video_id: UUID) -> DownloadResult:
        with self._container.uow():
            self._container.message_bus().handle(
                MarkFailed(video_id=video_id, reason="worker stalled")
            )
        return _RESULT


class TestDownloadNextPending:
    def test_claims_downloads_and_marks_downloaded(self, container: Container) -> None:
        uow = container.uow()
        with uow:
            video = VideoFactory()
            uow.videos.add(video)
            video_id = video.id

        did_work = download_next_pending(
            uow,
            container.message_bus(),
            _FakeDownloader(result=_RESULT),
            _HEARTBEAT_SEC,
        )

        assert did_work is True
        with uow:
            loaded = uow.videos.get(video_id)
            assert loaded.status is VideoStatus.DOWNLOADED
            assert loaded.original_path == "x.mp4"
            assert loaded.source_metadata == _METADATA
            assert loaded.source_file_available is True

    def test_download_failure_marks_failed(self, container: Container) -> None:
        uow = container.uow()
        with uow:
            video = VideoFactory()
            uow.videos.add(video)
            video_id = video.id

        did_work = download_next_pending(
            uow,
            container.message_bus(),
            _FakeDownloader(error=RuntimeError("boom")),
            _HEARTBEAT_SEC,
        )

        assert did_work is True
        with uow:
            loaded = uow.videos.get(video_id)
            assert loaded.status is VideoStatus.FAILED
            assert loaded.error_message == "boom"

    @pytest.mark.parametrize("interruption", [SystemExit(143), KeyboardInterrupt()])
    def test_interrupted_download_marks_failed_and_propagates(
        self, container: Container, interruption: BaseException
    ) -> None:
        uow = container.uow()
        with uow:
            video = VideoFactory()
            uow.videos.add(video)
            video_id = video.id

        with pytest.raises(type(interruption)):
            download_next_pending(
                uow,
                container.message_bus(),
                _FakeDownloader(error=interruption),
                _HEARTBEAT_SEC,
            )

        with uow:
            loaded = uow.videos.get(video_id)
            assert loaded.status is VideoStatus.FAILED
            assert loaded.error_message == "worker shut down"

    def test_returns_false_when_nothing_pending(self, container: Container) -> None:
        uow = container.uow()

        did_work = download_next_pending(
            uow,
            container.message_bus(),
            _FakeDownloader(result=_RESULT),
            _HEARTBEAT_SEC,
        )

        assert did_work is False

    def test_outcome_after_a_sweep_is_dropped(self, container: Container) -> None:
        uow = container.uow()
        with uow:
            video = VideoFactory()
            uow.videos.add(video)
            video_id = video.id

        did_work = download_next_pending(
            uow, container.message_bus(), _SweptMidDownload(container), _HEARTBEAT_SEC
        )

        assert did_work is True
        with uow:
            loaded = uow.videos.get(video_id)
            assert loaded.status is VideoStatus.FAILED
            assert loaded.error_message == "worker stalled"
