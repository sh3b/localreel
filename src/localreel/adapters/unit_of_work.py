from typing import Self

from sqlalchemy.orm import Session, scoped_session, sessionmaker

from localreel.adapters.repository import PostgresVideoRepository
from localreel.domain.abstractions.unit_of_work import AbstractUnitOfWork


class PostgresUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        # One session per thread. The API shares this one object across its
        # request threads; a session kept on self would be swapped between
        # requests halfway through their transactions.
        self._sessions = scoped_session(session_factory)

    def __enter__(self) -> Self:
        # A nested block would share the outer session and commit it half done.
        if self._sessions.registry.has():
            raise RuntimeError("A unit of work is already open on this thread")
        self._sessions()
        return self

    @property
    def videos(self) -> PostgresVideoRepository:
        if not self._sessions.registry.has():
            raise RuntimeError("No unit of work is open on this thread")
        return PostgresVideoRepository(self._sessions())

    def commit(self) -> None:
        self._sessions.commit()

    def rollback(self) -> None:
        self._sessions.rollback()

    def _close(self) -> None:
        self._sessions.remove()
