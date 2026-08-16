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
    ResetDownload,
    StartDownload,
    SubmitURL,
)
from localreel.domain.exceptions import DuplicateVideo, UnsupportedSource, VideoNotFound
from localreel.domain.value_objects import VideoSource, VideoStatus
from tests.factories import SourceMetadataFactory, VideoFactory


class TestSubmitURL:
    def test_persists_a_pending_video(
        self, container: Container, session: Session
    ) -> None:
        with container.uow():
            container.message_bus().handle(
                SubmitURL(url="https://youtu.be/jNQXAC9IVRw")
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
                container.message_bus().handle(SubmitURL(url=url))

        assert session.scalar(select(func.count()).select_from(VideoORM)) == 1

    def test_losing_a_race_to_the_same_video_rolls_back(
        self, container: Container, session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        with container.uow():
            container.message_bus().handle(
                SubmitURL(url="https://youtu.be/jNQXAC9IVRw")
            )
        # Both submits passed the check: the second one only meets the constraint.
        monkeypatch.setattr(PostgresVideoRepository, "exists", lambda *_, **__: False)

        with pytest.raises(DuplicateVideo), container.uow():
            container.message_bus().handle(
                SubmitURL(url="https://youtu.be/jNQXAC9IVRw")
            )

        assert session.scalar(select(func.count()).select_from(VideoORM)) == 1

    def test_unsupported_url_raises_and_persists_nothing(
        self, container: Container, session: Session
    ) -> None:
        with pytest.raises(UnsupportedSource), container.uow():
            container.message_bus().handle(SubmitURL(url="https://example.com/v/1"))

        assert session.scalar(select(func.count()).select_from(VideoORM)) == 0


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
