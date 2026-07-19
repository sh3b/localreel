from collections.abc import Iterator

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from localreel.containers import Container


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """One engine and connection pool for the whole run."""
    engine = Container().engine()
    yield engine
    engine.dispose()


@pytest.fixture
def container(engine: Engine) -> Iterator[Container]:
    """Each test runs in one transaction, rolled back at the end. Session
    commits become savepoint releases inside it, so code under test commits
    and reads normally but nothing persists and no cleanup is needed."""
    container = Container()
    with engine.connect() as connection:
        transaction = connection.begin()
        test_session_factory = sessionmaker(
            bind=connection, autoflush=True, join_transaction_mode="create_savepoint"
        )
        with (
            container.engine.override(engine),
            container.session_factory.override(test_session_factory),
        ):
            yield container
        transaction.rollback()


@pytest.fixture
def session_factory(container: Container) -> sessionmaker[Session]:
    return container.session_factory()


@pytest.fixture
def session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    with session_factory() as session:
        yield session
