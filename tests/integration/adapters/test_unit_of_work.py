import pytest
from sqlalchemy.orm import Session, sessionmaker

from localreel.adapters.orm import VideoORM
from localreel.containers import Container
from tests.factories import VideoFactory


class TestPostgresUnitOfWork:
    def test_clean_exit_commits(
        self, container: Container, session_factory: sessionmaker[Session]
    ) -> None:
        video = VideoFactory.build()

        with container.uow() as uow:
            uow.videos.add(video)

        with session_factory() as session:
            assert session.get(VideoORM, video.id) is not None

    def test_exception_rolls_back(
        self, container: Container, session_factory: sessionmaker[Session]
    ) -> None:
        video = VideoFactory.build()

        with pytest.raises(RuntimeError), container.uow() as uow:
            uow.videos.add(video)
            raise RuntimeError("boom")

        with session_factory() as session:
            assert session.get(VideoORM, video.id) is None
