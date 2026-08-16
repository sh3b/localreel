import logging
import time

import pytest

from localreel.entrypoints.worker import main as worker_main
from localreel.entrypoints.worker.main import Worker
from localreel.service_layer.download_service import DownloadService


class StopLoop(Exception):
    pass


class FakeDownloadService(DownloadService):
    def __init__(self, results: list[bool]) -> None:
        self._results = iter(results)
        self.calls = 0
        self.resets_before_first_call: int | None = None
        self._resets = 0

    def reset_interrupted_downloads(self) -> None:
        self._resets += 1

    def download_next(self) -> bool:
        if self.calls == 0:
            self.resets_before_first_call = self._resets
        self.calls += 1
        try:
            return next(self._results)
        except StopIteration:
            raise StopLoop from None


class TestWorker:
    @pytest.fixture
    def sleeps(self, monkeypatch: pytest.MonkeyPatch) -> list[float]:
        recorded: list[float] = []
        monkeypatch.setattr(time, "sleep", recorded.append)
        return recorded

    def test_sleeps_for_the_poll_interval_when_there_is_no_work(
        self, sleeps: list[float]
    ) -> None:
        service = FakeDownloadService([False, False])

        with pytest.raises(StopLoop):
            Worker(service=service, poll_interval_sec=5).run()

        assert sleeps == [5, 5]

    def test_takes_the_next_video_without_sleeping_while_there_is_work(
        self, sleeps: list[float]
    ) -> None:
        service = FakeDownloadService([True, True, True])

        with pytest.raises(StopLoop):
            Worker(service=service, poll_interval_sec=5).run()

        assert service.calls == 4
        assert sleeps == []

    def test_resets_interrupted_downloads_once_before_the_first_claim(
        self, sleeps: list[float]
    ) -> None:
        service = FakeDownloadService([True, False])

        with pytest.raises(StopLoop):
            Worker(service=service, poll_interval_sec=5).run()

        assert service.resets_before_first_call == 1


class TestMain:
    def test_runs_a_worker_built_from_the_container(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        started: list[Worker] = []
        monkeypatch.setattr(Worker, "run", lambda self: started.append(self))
        monkeypatch.setattr(logging, "basicConfig", lambda **_: None)

        worker_main.main()

        assert len(started) == 1
