import threading

import pytest
from sqlalchemy.orm import Session, sessionmaker

from localreel.adapters.unit_of_work import PostgresUnitOfWork


class TestPostgresUnitOfWork:
    def test_threads_running_at_once_each_get_their_own_session(self) -> None:
        uow = PostgresUnitOfWork(sessionmaker())
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

        assert len(seen) == 2
        assert seen[0] is not seen[1]

    def test_refuses_a_nested_block_on_the_same_thread(self) -> None:
        uow = PostgresUnitOfWork(sessionmaker())

        with uow:
            with pytest.raises(RuntimeError):
                with uow:
                    pass

    def test_refuses_repository_access_outside_a_block(self) -> None:
        uow = PostgresUnitOfWork(sessionmaker())

        with pytest.raises(RuntimeError):
            _ = uow.videos
