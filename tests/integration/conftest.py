from collections.abc import Callable, Iterator
from uuid import UUID

import pytest
from dependency_injector import providers
from sqlalchemy import Engine, create_engine, delete
from sqlalchemy.orm import Session, sessionmaker

from localreel.adapters import orm
from localreel.containers import Container
from localreel.domain.models.video import Video


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """Shared by every test. The lock timeout turns a blocked query into a failure
    instead of a hung test run."""
    engine = create_engine(
        Container().settings().db_url,
        connect_args={"options": "-c lock_timeout=5s"},
    )
    yield engine

    engine.dispose()


@pytest.fixture
def container(engine: Engine) -> Iterator[Container]:
    """Each test runs in one transaction, rolled back at the end. Session
    commits become savepoint releases inside it, so code under test commits
    and reads normally but nothing ever persists, no cleanup needed."""
    container = Container()
    container.engine.override(providers.Object(engine))
    connection = engine.connect()
    transaction = connection.begin()
    container.session_factory.override(
        sessionmaker(
            bind=connection, autoflush=True, join_transaction_mode="create_savepoint"
        )
    )
    yield container

    transaction.rollback()
    connection.close()


@pytest.fixture
def session(container: Container) -> Session:
    return container.session_factory()()


@pytest.fixture
def real_session_factory(engine: Engine) -> sessionmaker[Session]:
    """For what the savepoint recipe can't show: behaviour across connections.
    Each session gets its own connection and commits for real."""
    return sessionmaker(bind=engine, autoflush=True)


@pytest.fixture
def commit_video(
    real_session_factory: sessionmaker[Session],
) -> Iterator[Callable[[Video], None]]:
    """Commits a video for real and deletes it by id after the test."""
    video_ids: list[UUID] = []

    def commit(video: Video) -> None:
        video_ids.append(video.id)
        with real_session_factory() as session:
            session.add(video)
            session.commit()

    yield commit

    with real_session_factory() as session:
        session.execute(delete(orm.videos).where(orm.videos.c.id.in_(video_ids)))
        session.commit()
