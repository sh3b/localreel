from typing import Self

from sqlalchemy.orm import Session, sessionmaker

from localreel.adapters.repository import (
    PostgresDownloadJobRepository,
    PostgresVideoRepository,
)
from localreel.domain.abstractions.unit_of_work import AbstractUnitOfWork


class PostgresUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def __enter__(self) -> Self:
        self._session = self._session_factory()
        self.videos = PostgresVideoRepository(self._session)
        self.download_jobs = PostgresDownloadJobRepository(self._session)
        return self

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

    def _close(self) -> None:
        self._session.close()
