from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from localreel.domain.messages import Event
from localreel.domain.repository import AbstractVideoRepository


class AbstractUnitOfWork(ABC):
    videos: AbstractVideoRepository

    def __init__(self) -> None:
        self._commit_on_exit = True

    def __call__(self, *, commit: bool = True) -> Self:
        """with uow(commit=False): a read-only block; it rolls back on exit."""
        self._commit_on_exit = commit
        return self

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            if exc_type is None and self._commit_on_exit:
                self.commit()
            else:
                self.rollback()
        finally:
            self._commit_on_exit = True
            self._close()

    @abstractmethod
    def collect_events(self) -> list[Event]:
        """Hands over, once, the events raised by the videos it holds."""
        raise NotImplementedError

    @abstractmethod
    def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def rollback(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def _close(self) -> None:
        raise NotImplementedError
