from dataclasses import dataclass

import pytest

from localreel.domain.messages import Command, Event, Message
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
class DoFollowUpThing(Command):
    pass


class TestCommands:
    def test_dispatches_to_registered_handler(self):
        handled: list[DoThing] = []
        bus = MessageBus(
            command_handlers={DoThing: handled.append},
            event_handlers={},
        )

        command = DoThing()
        bus.handle(command)

        assert handled == [command]

    def test_unknown_command_raises(self):
        bus = MessageBus(command_handlers={}, event_handlers={})

        with pytest.raises(KeyError, match="DoThing"):
            bus.handle(DoThing())


class TestEvents:
    def test_messages_returned_by_handlers_are_dispatched(self):
        done: list[ThingDone] = []
        bus = MessageBus(
            command_handlers={DoThing: lambda cmd: [ThingDone()]},
            event_handlers={ThingDone: [done.append]},
        )

        bus.handle(DoThing())

        assert len(done) == 1

    def test_all_handlers_of_an_event_run(self):
        first: list[ThingDone] = []
        second: list[ThingDone] = []
        bus = MessageBus(
            command_handlers={},
            event_handlers={ThingDone: [first.append, second.append]},
        )

        event = ThingDone()
        bus.handle(event)

        assert first == [event]
        assert second == [event]

    def test_messages_returned_by_event_handlers_are_dispatched(self):
        handled: list[DoThing] = []
        bus = MessageBus(
            command_handlers={DoThing: handled.append},
            event_handlers={ThingDone: [lambda event: [DoThing()]]},
        )

        bus.handle(ThingDone())

        assert len(handled) == 1

    def test_unregistered_event_raises(self):
        bus = MessageBus(command_handlers={}, event_handlers={})

        with pytest.raises(KeyError, match="ThingDone"):
            bus.handle(ThingDone())

    def test_event_registered_with_empty_handler_list_is_a_noop(self):
        bus = MessageBus(command_handlers={}, event_handlers={ThingDone: []})

        bus.handle(ThingDone())


def test_emitted_messages_join_the_back_of_the_queue():
    """A message emitted by a handler is not handled on the spot, it
    is added to the end of the queue."""
    order: list[type] = []

    def handle_do_thing(command: DoThing) -> list[Message]:
        order.append(DoThing)
        return [ThingDone(), OtherThingDone()]

    def handle_thing_done(event: ThingDone) -> list[Message]:
        order.append(ThingDone)
        return [DoFollowUpThing()]

    def handle_other_thing_done(event: OtherThingDone) -> None:
        order.append(OtherThingDone)

    def handle_follow_up(command: DoFollowUpThing) -> None:
        order.append(DoFollowUpThing)

    bus = MessageBus(
        command_handlers={
            DoThing: handle_do_thing,
            DoFollowUpThing: handle_follow_up,
        },
        event_handlers={
            ThingDone: [handle_thing_done],
            OtherThingDone: [handle_other_thing_done],
        },
    )

    bus.handle(DoThing())

    assert order == [DoThing, ThingDone, OtherThingDone, DoFollowUpThing]


def test_message_that_is_neither_command_nor_event_raises():
    bus = MessageBus(command_handlers={}, event_handlers={})

    with pytest.raises(TypeError):
        bus.handle(object())  # type: ignore[arg-type]
