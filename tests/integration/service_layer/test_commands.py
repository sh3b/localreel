import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from localreel.adapters.orm import VideoORM
from localreel.containers import Container
from localreel.domain.commands import SubmitURL
from localreel.domain.exceptions import UnsupportedSource
from localreel.domain.types import VideoSource, VideoStatus


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

    def test_unsupported_url_raises_and_persists_nothing(
        self, container: Container, session: Session
    ) -> None:
        with pytest.raises(UnsupportedSource), container.uow():
            container.message_bus().handle(SubmitURL(url="https://example.com/v/1"))

        assert session.scalar(select(func.count()).select_from(VideoORM)) == 0
