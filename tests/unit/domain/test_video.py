from uuid import uuid7

import pytest

from localreel.domain.exceptions import UnsupportedSource
from localreel.domain.models.video import Video
from localreel.domain.types import VideoSource, VideoStatus


class TestCreate:
    def test_starts_pending_with_its_source(self) -> None:
        video_id = uuid7()

        video = Video.create(id=video_id, source_url="https://youtu.be/jNQXAC9IVRw")

        assert video.id == video_id
        assert video.source is VideoSource.YOUTUBE
        assert video.source_url == "https://youtu.be/jNQXAC9IVRw"
        assert video.status is VideoStatus.PENDING

    def test_rejects_an_unsupported_url(self) -> None:
        with pytest.raises(UnsupportedSource):
            Video.create(id=uuid7(), source_url="https://vimeo.com/12345")
