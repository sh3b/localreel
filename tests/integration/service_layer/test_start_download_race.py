import threading
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, delete
from sqlalchemy.orm import Session

from localreel.adapters.orm import VideoORM
from localreel.containers import Container
from localreel.domain.commands import StartDownload
from localreel.domain.exceptions import InvalidStatusTransition
from localreel.domain.models.video import Video
from localreel.domain.value_objects import VideoStatus
from tests.factories import VideoFactory


class TestStartDownloadRace:
    """Two transactions must really commit here, so these tests skip the
    rolled-back test transaction and delete their row afterwards."""

    @pytest.fixture
    def committing_container(self, engine: Engine) -> Iterator[Container]:
        container = Container()
        with container.engine.override(engine):
            yield container

    @pytest.fixture
    def video(self, engine: Engine) -> Iterator[Video]:
        video = VideoFactory.build()
        with Session(engine) as session, session.begin():
            session.add(
                VideoORM(
                    id=video.id,
                    source=video.source,
                    source_url=video.source_url,
                    source_key=video.source_key,
                    status=video.status,
                )
            )
        yield video
        with Session(engine) as session, session.begin():
            session.execute(delete(VideoORM).where(VideoORM.id == video.id))

    def test_a_second_start_waits_for_the_first_then_is_refused(
        self, committing_container: Container, video: Video, engine: Engine
    ) -> None:
        container = committing_container
        errors: list[Exception] = []

        def second_worker() -> None:
            try:
                with container.uow():
                    container.message_bus().handle(StartDownload(video_id=video.id))
            except Exception as exc:
                errors.append(exc)

        with container.uow():
            container.message_bus().handle(StartDownload(video_id=video.id))
            second = threading.Thread(target=second_worker)
            second.start()
            second.join(timeout=0.5)
            assert second.is_alive()

        second.join(timeout=5)
        assert not second.is_alive()
        assert len(errors) == 1
        assert isinstance(errors[0], InvalidStatusTransition)
        with Session(engine) as session:
            assert session.get_one(VideoORM, video.id).status is VideoStatus.DOWNLOADING
