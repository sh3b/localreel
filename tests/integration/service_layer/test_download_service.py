from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from localreel.adapters.orm import VideoORM
from localreel.adapters.repository import PostgresVideoRepository
from localreel.containers import Container
from localreel.domain.commands import StartDownload
from localreel.domain.downloader import AbstractDownloader, DownloadResult
from localreel.domain.value_objects import VideoStatus
from localreel.service_layer.download_service import DownloadService
from tests.factories import SourceMetadataFactory, VideoFactory


class FakeDownloader(AbstractDownloader):
    def __init__(self, error: Exception | None = None) -> None:
        self.downloaded: list[str] = []
        self.discarded: list[UUID] = []
        self._error = error

    def download(self, *, url: str, video_id: UUID) -> DownloadResult:
        self.downloaded.append(url)
        if self._error is not None:
            raise self._error
        return DownloadResult(
            file_path=f"{video_id}.webm",
            thumbnail_path=f"{video_id}.webp",
            metadata=SourceMetadataFactory.build(),
        )

    def discard(self, *, video_id: UUID) -> None:
        self.discarded.append(video_id)


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
        assert row.file_path == f"{video_id}.webm"
        assert row.thumbnail_path == f"{video_id}.webp"
        assert row.source_title == "Me at the zoo"
        assert downloader.discarded == []

    def test_marks_the_video_failed_when_the_download_raises(
        self, container: Container, session: Session
    ) -> None:
        video_id = self._pending_video(container)
        downloader = FakeDownloader(error=RuntimeError("Video unavailable"))

        self._service(container, downloader).download_next()

        row = session.get_one(VideoORM, video_id)
        assert row.status is VideoStatus.FAILED
        assert row.error == "Video unavailable"
        assert downloader.discarded == [video_id]

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
        monkeypatch.setattr(PostgresVideoRepository, "next_pending", lambda _: video.id)
        downloader = FakeDownloader()

        did_work = self._service(container, downloader).download_next()

        assert did_work is True
        assert downloader.downloaded == []
        assert session.get_one(VideoORM, video.id).status is VideoStatus.DOWNLOADING

    def test_reset_puts_interrupted_downloads_back_to_pending(
        self, container: Container, session: Session
    ) -> None:
        video_id = self._pending_video(container)
        with container.uow():
            container.message_bus().handle(StartDownload(video_id=video_id))

        downloader = FakeDownloader()

        self._service(container, downloader).reset_interrupted_downloads()

        assert session.get_one(VideoORM, video_id).status is VideoStatus.PENDING
        assert downloader.discarded == []

    def test_reset_fails_a_video_whose_attempts_are_used_up(
        self, container: Container, session: Session
    ) -> None:
        video_id = self._pending_video(container)
        downloader = FakeDownloader()
        service = self._service(container, downloader)
        for _ in range(3):
            with container.uow():
                container.message_bus().handle(StartDownload(video_id=video_id))
            service.reset_interrupted_downloads()

        row = session.get_one(VideoORM, video_id)
        assert row.status is VideoStatus.FAILED
        assert row.error == "Download interrupted 3 times"
        assert downloader.discarded == [video_id]

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
