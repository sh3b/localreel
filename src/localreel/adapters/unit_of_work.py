from typing import Self

from sqlalchemy.orm import Session, sessionmaker

from localreel.adapters.repository import PostgresVideoRepository
from localreel.domain.messages import Event
from localreel.domain.unit_of_work import AbstractUnitOfWork


class PostgresUnitOfWork(AbstractUnitOfWork):
    videos: PostgresVideoRepository

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        super().__init__()
        self._session_factory = session_factory

    def __enter__(self) -> Self:
        self._session = self._session_factory()
        self.videos = PostgresVideoRepository(self._session)
        return self

    def collect_events(self) -> list[Event]:
        return [
            event
            for video in self.videos.seen.values()
            for event in video.collect_events()
        ]

    def commit(self) -> None:
        for video in self.videos.seen.values():
            self.videos.save(video)
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

    def _close(self) -> None:
        self._session.close()
