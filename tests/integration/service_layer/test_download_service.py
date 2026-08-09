from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from localreel.adapters.orm import VideoORM
from localreel.adapters.repository import PostgresVideoRepository
from localreel.containers import Container
from localreel.domain.commands import StartDownload
from localreel.domain.downloader import AbstractDownloader
from localreel.domain.value_objects import VideoStatus
from localreel.service_layer.download_service import DownloadService
from tests.factories import VideoFactory


class FakeDownloader(AbstractDownloader):
    def __init__(self, error: Exception | None = None) -> None:
        self.downloaded: list[str] = []
        self._error = error

    def download(self, *, url: str, video_id: UUID) -> str:
        self.downloaded.append(url)
        if self._error is not None:
            raise self._error
        return f"/downloads/{video_id}.mp4"


class TestDownloadService:
    def test_downloads_a_pending_video_and_marks_it_ready(
        self, container: Container, session: Session
    ) -> None:
        video_id = self._pending_video(container)
        downloader = FakeDownloader()

        did_work = self._service(container, downloader).download_next()

        assert did_work is True
        assert downloader.downloaded == ["https://youtu.be/jNQXAC9IVRw"]
        row = session.get_one(VideoORM, video_id)
        assert row.status is VideoStatus.READY
        assert row.file_path == f"/downloads/{video_id}.mp4"

    def test_marks_the_video_failed_when_the_download_raises(
        self, container: Container, session: Session
    ) -> None:
        video_id = self._pending_video(container)
        downloader = FakeDownloader(error=RuntimeError("Video unavailable"))

        self._service(container, downloader).download_next()

        row = session.get_one(VideoORM, video_id)
        assert row.status is VideoStatus.FAILED
        assert row.error == "Video unavailable"

    def test_skips_a_video_another_worker_already_took(
        self,
        container: Container,
        session: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        video = VideoFactory.build()
        with container.uow() as uow:
            uow.videos.add(video)
        with container.uow():
            container.message_bus().handle(StartDownload(video_id=video.id))
        monkeypatch.setattr(PostgresVideoRepository, "next_pending", lambda _: video)
        downloader = FakeDownloader()

        did_work = self._service(container, downloader).download_next()

        assert did_work is True
        assert downloader.downloaded == []
        assert session.get_one(VideoORM, video.id).status is VideoStatus.DOWNLOADING

    def test_does_nothing_without_pending_videos(self, container: Container) -> None:
        downloader = FakeDownloader()

        did_work = self._service(container, downloader).download_next()

        assert did_work is False
        assert downloader.downloaded == []

    @staticmethod
    def _service(
        container: Container, downloader: AbstractDownloader
    ) -> DownloadService:
        with container.downloader.override(downloader):
            return container.download_service()

    @staticmethod
    def _pending_video(container: Container) -> UUID:
        video = VideoFactory.build(source_url="https://youtu.be/jNQXAC9IVRw")
        with container.uow() as uow:
            uow.videos.add(video)
        return video.id
