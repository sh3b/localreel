from collections.abc import Iterator

import pytest
from sqlalchemy import Connection, Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from localreel.settings import Settings


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    engine = create_engine(Settings().db_url)
    yield engine
    engine.dispose()


@pytest.fixture
def connection(engine: Engine) -> Iterator[Connection]:
    """Each test runs in one transaction, rolled back at the end. Session
    commits become savepoint releases inside it, so code under test commits
    and reads normally but nothing persists and no cleanup is needed."""
    with engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()


@pytest.fixture
def session_factory(connection: Connection) -> sessionmaker[Session]:
    return sessionmaker(bind=connection, join_transaction_mode="create_savepoint")


@pytest.fixture
def session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    with session_factory() as session:
        yield session
