from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session, sessionmaker

from localreel.containers import Container


@pytest.fixture
def container() -> Iterator[Container]:
    """Each test runs in one transaction, rolled back at the end. Session
    commits become savepoint releases inside it, so code under test commits
    and reads normally but nothing ever persists, no cleanup needed."""
    container = Container()
    connection = container.engine().connect()
    transaction = connection.begin()
    container.session_factory.override(
        sessionmaker(
            bind=connection, autoflush=True, join_transaction_mode="create_savepoint"
        )
    )
    yield container

    transaction.rollback()
    connection.close()
    container.engine().dispose()


@pytest.fixture
def session(container: Container) -> Session:
    return container.session_factory()()
