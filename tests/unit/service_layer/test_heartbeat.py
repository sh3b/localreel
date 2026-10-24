import threading
import time

from localreel.domain.abstractions.repository import AbstractVideoRepository
from localreel.domain.abstractions.unit_of_work import AbstractUnitOfWork
from localreel.domain.commands import RecordHeartbeat
from localreel.service_layer.heartbeat import Heartbeat
from localreel.service_layer.message_bus import MessageBus
from tests.factories.video import VideoFactory


class _FakeUnitOfWork(AbstractUnitOfWork):
    @property
    def videos(self) -> AbstractVideoRepository:
        raise NotImplementedError

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def _close(self) -> None:
        pass


class _Beats:
    """Counts beats; fails the first `failures` of them."""

    def __init__(self, wanted: int, failures: int = 0) -> None:
        self.count = 0
        self.reached = threading.Event()
        self._wanted = wanted
        self._failures = failures

    def __call__(self, cmd: RecordHeartbeat) -> None:
        self.count += 1
        if self.count >= self._wanted:
            self.reached.set()
        if self.count <= self._failures:
            raise RuntimeError("database away")


def _heartbeat(beats: _Beats, interval_sec: float) -> Heartbeat:
    bus = MessageBus(command_handlers={RecordHeartbeat: beats}, event_handlers={})
    return Heartbeat(_FakeUnitOfWork(), bus, VideoFactory().id, interval_sec)


class TestHeartbeat:
    def test_beats_while_the_block_runs(self) -> None:
        beats = _Beats(wanted=3)

        with _heartbeat(beats, interval_sec=0.01):
            assert beats.reached.wait(timeout=5)

    def test_stops_beating_when_the_block_exits(self) -> None:
        beats = _Beats(wanted=1)
        with _heartbeat(beats, interval_sec=0.01):
            assert beats.reached.wait(timeout=5)
        count = beats.count

        time.sleep(0.05)

        assert beats.count == count

    def test_a_failed_beat_does_not_end_the_beats(self) -> None:
        beats = _Beats(wanted=3, failures=2)

        with _heartbeat(beats, interval_sec=0.01):
            assert beats.reached.wait(timeout=5)

    def test_no_beat_before_the_first_interval(self) -> None:
        beats = _Beats(wanted=1)

        with _heartbeat(beats, interval_sec=3600):
            pass

        assert beats.count == 0
