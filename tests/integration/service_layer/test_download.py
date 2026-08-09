from uuid import UUID

from localreel.containers import Container
from localreel.domain.abstractions.downloader import AbstractDownloader
from localreel.domain.types import VideoStatus
from localreel.service_layer.download import download_next_pending
from tests.factories.video import VideoFactory


class _FakeDownloader(AbstractDownloader):
    def __init__(self, *, path: str | None = None, error: Exception | None = None):
        self._path = path
        self._error = error

    def download(self, *, url: str, video_id: UUID) -> str:
        if self._error is not None:
            raise self._error
        assert self._path is not None
        return self._path


class TestDownloadNextPending:
    def test_claims_downloads_and_marks_downloaded(self, container: Container) -> None:
        uow = container.uow()
        with uow:
            video = VideoFactory()
            uow.videos.add(video)
            video_id = video.id

        did_work = download_next_pending(
            uow, container.message_bus(), _FakeDownloader(path="/data/x.mp4")
        )

        assert did_work is True
        with uow:
            loaded = uow.videos.get(video_id)
            assert loaded.status is VideoStatus.DOWNLOADED
            assert loaded.original_path == "/data/x.mp4"
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
            uow, container.message_bus(), _FakeDownloader(path="/data/x.mp4")
        )

        assert did_work is False
