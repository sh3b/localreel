from typing import Any
from uuid import uuid7

import factory

from localreel.domain.models.video import Video
from localreel.domain.value_objects import SourceMetadata


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


class SourceMetadataFactory(factory.Factory[SourceMetadata]):
    class Meta:
        model = SourceMetadata
        strategy = factory.BUILD_STRATEGY

    title = "Me at the zoo"
    description = "The first video on YouTube."
    uploader = "jawed"
    view_count = 448473011
    duration_sec = 19
    raw = factory.LazyFunction(lambda: {"id": "jNQXAC9IVRw", "extractor": "youtube"})
