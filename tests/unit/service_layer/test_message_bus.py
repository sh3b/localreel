from dataclasses import dataclass

import pytest

from localreel.domain.messages import Command, Event
from localreel.domain.unit_of_work import AbstractUnitOfWork
from localreel.service_layer.message_bus import MessageBus


@dataclass
class DoThing(Command):
    pass


@dataclass
class ThingDone(Event):
    pass


@dataclass
class OtherThingDone(Event):
    pass


@dataclass
class FollowUpDone(Event):
    pass


class FakeUnitOfWork(AbstractUnitOfWork):
    """Handlers put events in `raised`, as a changed video would."""

    def __init__(self) -> None:
        super().__init__()
        self.raised: list[Event] = []

    def collect_events(self) -> list[Event]:
        events = self.raised
        self.raised = []
        return events

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def _close(self) -> None:
        pass


class TestCommands:
    def test_dispatches_to_registered_handler(self):
        handled: list[DoThing] = []
        bus = MessageBus(
            FakeUnitOfWork(),
            command_handlers={DoThing: handled.append},
            event_handlers={},
        )

        command = DoThing()
        bus.handle(command)

        assert handled == [command]

    def test_unknown_command_raises(self):
        bus = MessageBus(FakeUnitOfWork(), command_handlers={}, event_handlers={})

        with pytest.raises(KeyError, match="DoThing"):
            bus.handle(DoThing())


class TestEvents:
    def test_events_raised_by_a_command_handler_are_dispatched(self):
        uow = FakeUnitOfWork()
        done: list[ThingDone] = []
        bus = MessageBus(
            uow,
            command_handlers={DoThing: lambda cmd: uow.raised.append(ThingDone())},
            event_handlers={ThingDone: [done.append]},
        )

        bus.handle(DoThing())

        assert len(done) == 1

    def test_all_handlers_of_an_event_run(self):
        first: list[ThingDone] = []
        second: list[ThingDone] = []
        bus = MessageBus(
            FakeUnitOfWork(),
            command_handlers={},
            event_handlers={ThingDone: [first.append, second.append]},
        )

        event = ThingDone()
        bus.handle(event)

        assert first == [event]
        assert second == [event]

    def test_events_raised_by_an_event_handler_are_dispatched(self):
        uow = FakeUnitOfWork()
        done: list[FollowUpDone] = []
        bus = MessageBus(
            uow,
            command_handlers={},
            event_handlers={
                ThingDone: [lambda event: uow.raised.append(FollowUpDone())],
                FollowUpDone: [done.append],
            },
        )

        bus.handle(ThingDone())

        assert len(done) == 1

    def test_unregistered_event_raises(self):
        bus = MessageBus(FakeUnitOfWork(), command_handlers={}, event_handlers={})

        with pytest.raises(KeyError, match="ThingDone"):
            bus.handle(ThingDone())

    def test_event_registered_with_empty_handler_list_is_a_noop(self):
        bus = MessageBus(
            FakeUnitOfWork(), command_handlers={}, event_handlers={ThingDone: []}
        )

        bus.handle(ThingDone())


def test_raised_events_join_the_back_of_the_queue():
    """An event raised by a handler is not handled on the spot, it is added
    to the end of the queue."""
    uow = FakeUnitOfWork()
    order: list[type] = []

    def handle_do_thing(command: DoThing) -> None:
        order.append(DoThing)
        uow.raised.extend([ThingDone(), OtherThingDone()])

    def handle_thing_done(event: ThingDone) -> None:
        order.append(ThingDone)
        uow.raised.append(FollowUpDone())

    def handle_other_thing_done(event: OtherThingDone) -> None:
        order.append(OtherThingDone)

    def handle_follow_up_done(event: FollowUpDone) -> None:
        order.append(FollowUpDone)

    bus = MessageBus(
        uow,
        command_handlers={DoThing: handle_do_thing},
        event_handlers={
            ThingDone: [handle_thing_done],
            OtherThingDone: [handle_other_thing_done],
            FollowUpDone: [handle_follow_up_done],
        },
    )

    bus.handle(DoThing())

    assert order == [DoThing, ThingDone, OtherThingDone, FollowUpDone]


def test_message_that_is_neither_command_nor_event_raises():
    bus = MessageBus(FakeUnitOfWork(), command_handlers={}, event_handlers={})

    with pytest.raises(TypeError):
        bus.handle(object())  # type: ignore[arg-type]
