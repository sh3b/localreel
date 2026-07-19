import logging
from collections import deque
from collections.abc import Callable
from typing import Any

from localreel.domain.messages import Command, Event, Message

logger = logging.getLogger(__name__)

Handler = Callable[[Any], list[Message] | None]


class MessageBus:
    def __init__(
        self,
        command_handlers: dict[type[Command], Handler],
        event_handlers: dict[type[Event], list[Handler]],
    ) -> None:
        self.command_handlers = command_handlers
        self.event_handlers = event_handlers

    def handle(self, message: Message) -> None:
        queue: deque[Message] = deque([message])
        while queue:
            msg = queue.popleft()
            if isinstance(msg, Command):
                self._handle_command(msg, queue)
            elif isinstance(msg, Event):
                self._handle_event(msg, queue)
            else:
                raise TypeError(f"{msg!r} is neither a Command nor an Event")

    def _handle_command(self, command: Command, queue: deque[Message]) -> None:
        handler = self.command_handlers[type(command)]
        logger.debug("handling command %r", command)
        output = handler(command) or []
        queue.extend(output)

    def _handle_event(self, event: Event, queue: deque[Message]) -> None:
        handlers = self.event_handlers[type(event)]
        for handler in handlers:
            logger.debug("handling event %r with %r", event, handler)
            output = handler(event) or []
            queue.extend(output)
