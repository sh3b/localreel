import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from localreel.adapters.orm import VideoORM
from localreel.adapters.repository import PostgresVideoRepository
from localreel.containers import Container
from localreel.domain.commands import SubmitURL
from localreel.domain.exceptions import DuplicateVideo, UnsupportedSource
from localreel.domain.value_objects import VideoSource, VideoStatus


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
