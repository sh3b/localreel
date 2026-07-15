from typing import TYPE_CHECKING, Any
from uuid import uuid7

import factory

from localreel.domain.models.video import Video
from localreel.domain.types import VideoSource, VideoVisibility


class VideoFactory(factory.Factory[Video]):
    if TYPE_CHECKING:
        # Calling the factory class (VideoFactory()) runs the default strategy
        # and returns a Video, but the factory-boy stubs can't express that
        # through the metaclass, so declare it here. Type-only; never executed.
        def __new__(cls, **kwargs: Any) -> Video: ...  # type: ignore[misc]

    class Meta:
        model = Video

    id = factory.LazyFunction(uuid7)
    uploaded_by = factory.LazyFunction(uuid7)
    source = VideoSource.YOUTUBE
    source_url: factory.LazyAttribute[Video, str | None] = factory.LazyAttribute(
        lambda o: (
            None
            if o.source is VideoSource.LOCAL
            else "https://youtube.com/watch?v=dQw4w9WgXcQ"
        )
    )
    visibility = VideoVisibility.PRIVATE

    @classmethod
    def _create(cls, model_class: type[Video], *args: Any, **kwargs: Any) -> Video:
        # Route through the domain factory method so instances always start
        # in a state the state machine can actually reach.
        return model_class.create(**kwargs)

    @factory.post_generation
    def clear_events(
        obj: Video, create: bool, extracted: bool | None, **kwargs: Any
    ) -> None:
        # A factory-built video is test *arrangement*: drop the VideoIngested
        # creation event so tests assert only the events they cause.
        # Pass clear_events=False to keep it.
        if extracted is not False:
            obj.events.clear()
