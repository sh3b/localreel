import threading

import pytest
from sqlalchemy.orm import Session, sessionmaker

from localreel.adapters.unit_of_work import PostgresUnitOfWork


class RecordingSession(Session):
    """A session with no database behind it that remembers what was done to it."""

    made: list[RecordingSession] = []

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.committed = False
        self.closed = False
        RecordingSession.made.append(self)

    def commit(self) -> None:
        super().commit()
        self.committed = True

    def close(self) -> None:
        super().close()
        self.closed = True


@pytest.fixture
def uow() -> PostgresUnitOfWork:
    RecordingSession.made = []
    return PostgresUnitOfWork(sessionmaker(class_=RecordingSession))


class TestPostgresUnitOfWork:
    def test_threads_running_at_once_each_get_their_own_session(
        self, uow: PostgresUnitOfWork
    ) -> None:
        both_inside = threading.Barrier(2, timeout=5)
        seen: list[Session] = []

        def work() -> None:
            with uow:
                both_inside.wait()
                seen.append(uow.videos._session)

        threads = [threading.Thread(target=work) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        made = RecordingSession.made
        assert len(made) == 2
        assert {id(s) for s in seen} == {id(s) for s in made}
        assert all(s.committed and s.closed for s in made)

    def test_refuses_a_nested_block_on_the_same_thread(
        self, uow: PostgresUnitOfWork
    ) -> None:
        with uow:
            with pytest.raises(RuntimeError):
                with uow:
                    pass

    def test_refuses_repository_access_outside_a_block(
        self, uow: PostgresUnitOfWork
    ) -> None:
        with pytest.raises(RuntimeError):
            _ = uow.videos
