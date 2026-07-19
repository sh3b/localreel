from typing import Any
from uuid import uuid7

import factory

from localreel.domain.models.video import Video


class VideoFactory(factory.Factory[Video]):
    """Use VideoFactory.build(): it is the form mypy types as Video."""

    class Meta:
        model = Video
        strategy = factory.BUILD_STRATEGY

    id = factory.LazyFunction(uuid7)
    source_url = "https://youtu.be/jNQXAC9IVRw"

    @classmethod
    def _build(cls, model_class: type[Video], *args: Any, **kwargs: Any) -> Video:
        # Through the domain's own constructor, so source and status are derived.
        return model_class.create(**kwargs)
