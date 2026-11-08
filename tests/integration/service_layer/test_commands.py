from uuid import UUID, uuid7

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from localreel.adapters.orm import VideoORM
from localreel.adapters.repository import PostgresVideoRepository
from localreel.containers import Container
from localreel.domain.commands import (
    MarkFailed,
    MarkReady,
    PurgeVideo,
    RemoveVideo,
    ResetDownload,
    RetryVideo,
    StartDownload,
    SubmitURL,
)
from localreel.domain.exceptions import DuplicateVideo, VideoNotFound
from localreel.domain.value_objects import SourceURL, VideoSource, VideoStatus
from tests.factories import SourceMetadataFactory, VideoFactory
from tests.integration.service_layer.test_download_service import FakeDownloader


class TestSubmitURL:
    def test_persists_a_pending_video(
        self, container: Container, session: Session
    ) -> None:
        with container.uow():
            container.message_bus().handle(
                SubmitURL(source_url=SourceURL.parse("https://youtu.be/jNQXAC9IVRw"))
            )

        row = session.scalars(select(VideoORM)).one()
        assert row.source is VideoSource.YOUTUBE
        assert row.source_url == "https://youtu.be/jNQXAC9IVRw"
        assert row.status is VideoStatus.PENDING

    def test_resubmitting_the_same_video_keeps_one_row(
        self, container: Container, session: Session
    ) -> None:
        for url in (
            "https://youtu.be/jNQXAC9IVRw",
            "https://youtu.be/jNQXAC9IVRw",
            "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        ):
            with container.uow():
                container.message_bus().handle(
                    SubmitURL(source_url=SourceURL.parse(url))
                )

        assert session.scalar(select(func.count()).select_from(VideoORM)) == 1

    def test_losing_a_race_to_the_same_video_rolls_back(
        self, container: Container, session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        with container.uow():
            container.message_bus().handle(
                SubmitURL(source_url=SourceURL.parse("https://youtu.be/jNQXAC9IVRw"))
            )
        # Both submits passed the check: the second one only meets the constraint.
        monkeypatch.setattr(PostgresVideoRepository, "exists", lambda *_, **__: False)

        with pytest.raises(DuplicateVideo), container.uow():
            container.message_bus().handle(
                SubmitURL(source_url=SourceURL.parse("https://youtu.be/jNQXAC9IVRw"))
            )

        assert session.scalar(select(func.count()).select_from(VideoORM)) == 1


class TestDownloadCommands:
    def test_start_download_marks_the_video_downloading(
        self, container: Container, session: Session
    ) -> None:
        video_id = self._pending_video(container)

        with container.uow():
            container.message_bus().handle(StartDownload(video_id=video_id))

        assert session.get_one(VideoORM, video_id).status is VideoStatus.DOWNLOADING

    def test_reset_download_puts_the_video_back_to_pending(
        self, container: Container, session: Session
    ) -> None:
        video_id = self._downloading_video(container)

        with container.uow():
            container.message_bus().handle(ResetDownload(video_id=video_id))

        row = session.get_one(VideoORM, video_id)
        assert row.status is VideoStatus.PENDING
        assert row.attempts == 1

    def test_mark_ready_stores_the_download_result(
        self, container: Container, session: Session
    ) -> None:
        video_id = self._downloading_video(container)

        with container.uow():
            container.message_bus().handle(
                MarkReady(
                    video_id=video_id,
                    file_path="a.webm",
                    thumbnail_path="a.webp",
                    metadata=SourceMetadataFactory.build(),
                )
            )

        row = session.get_one(VideoORM, video_id)
        assert row.status is VideoStatus.READY
        assert row.file_path == "a.webm"
        assert row.thumbnail_path == "a.webp"
        assert row.source_title == "Me at the zoo"
        assert row.source_view_count == 448473011
        assert row.source_raw == {"id": "jNQXAC9IVRw", "extractor": "youtube"}

    def test_mark_failed_stores_the_reason(
        self, container: Container, session: Session
    ) -> None:
        video_id = self._downloading_video(container)

        with container.uow():
            container.message_bus().handle(
                MarkFailed(video_id=video_id, reason="Video unavailable")
            )

        row = session.get_one(VideoORM, video_id)
        assert row.status is VideoStatus.FAILED
        assert row.error == "Video unavailable"

    def test_retry_video_puts_a_failed_video_back_to_pending(
        self, container: Container, session: Session
    ) -> None:
        video_id = self._downloading_video(container)
        with container.uow():
            container.message_bus().handle(
                MarkFailed(video_id=video_id, reason="Video unavailable")
            )

        with container.uow():
            container.message_bus().handle(RetryVideo(video_id=video_id))

        row = session.get_one(VideoORM, video_id)
        assert row.status is VideoStatus.PENDING
        assert row.attempts == 0
        assert row.error is None

    def test_remove_video_hides_a_ready_video_and_keeps_its_files(
        self, container: Container, session: Session
    ) -> None:
        video_id = self._downloading_video(container)
        with container.uow():
            container.message_bus().handle(
                MarkReady(
                    video_id=video_id,
                    file_path=f"{video_id}.webm",
                    thumbnail_path=None,
                    metadata=SourceMetadataFactory.build(),
                )
            )
        downloader = FakeDownloader()

        with container.downloader.override(downloader), container.uow():
            container.message_bus().handle(RemoveVideo(video_id=video_id))

        assert session.get_one(VideoORM, video_id).status is VideoStatus.REMOVED
        assert downloader.discarded == []

    def test_purge_video_deletes_a_removed_row(
        self, container: Container, session: Session
    ) -> None:
        video_id = self._pending_video(container)
        with container.uow():
            container.message_bus().handle(RemoveVideo(video_id=video_id))

        with container.uow():
            container.message_bus().handle(PurgeVideo(video_id=video_id))

        assert session.get(VideoORM, video_id) is None

    def test_handled_events_are_not_left_on_the_video(
        self, container: Container
    ) -> None:
        video_id = self._downloading_video(container)

        with container.uow() as uow:
            container.message_bus().handle(
                MarkFailed(video_id=video_id, reason="Video unavailable")
            )

            assert uow.videos.get(video_id, lock=True).events == []

    def test_unknown_video_raises(self, container: Container) -> None:
        with pytest.raises(VideoNotFound), container.uow():
            container.message_bus().handle(StartDownload(video_id=uuid7()))

    @staticmethod
    def _pending_video(container: Container) -> UUID:
        video = VideoFactory.build()
        with container.uow() as uow:
            uow.videos.add(video)
        return video.id

    def _downloading_video(self, container: Container) -> UUID:
        video_id = self._pending_video(container)
        with container.uow():
            container.message_bus().handle(StartDownload(video_id=video_id))
        return video_id
