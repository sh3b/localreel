from uuid import uuid7

import pytest

from localreel.domain.events import VideoCreated, VideoUpdated
from localreel.domain.exceptions import InvalidStatusTransition, UnsupportedSource
from localreel.domain.models.video import Video
from localreel.domain.value_objects import VideoSource, VideoStatus
from tests.factories import VideoFactory


class TestCreate:
    def test_starts_pending_with_its_source(self) -> None:
        video_id = uuid7()

        video = Video.create(id=video_id, source_url="https://youtu.be/jNQXAC9IVRw")

        assert video.id == video_id
        assert video.source is VideoSource.YOUTUBE
        assert video.source_url == "https://youtu.be/jNQXAC9IVRw"
        assert video.source_key == "youtube:jNQXAC9IVRw"
        assert video.status is VideoStatus.PENDING

    def test_registers_that_it_was_created(self) -> None:
        video = Video.create(id=uuid7(), source_url="https://youtu.be/jNQXAC9IVRw")

        assert video.events == [VideoCreated(video)]

    def test_rejects_an_unsupported_url(self) -> None:
        with pytest.raises(UnsupportedSource):
            Video.create(id=uuid7(), source_url="https://vimeo.com/12345")


class TestDownloadTransitions:
    def test_start_download_moves_pending_to_downloading(self) -> None:
        video = VideoFactory.build()

        video.start_download()

        assert video.status is VideoStatus.DOWNLOADING

    def test_mark_ready_keeps_the_file_path(self) -> None:
        video = VideoFactory.build()
        video.start_download()

        video.mark_ready("/downloads/a.mp4")

        assert video.status is VideoStatus.READY
        assert video.file_path == "/downloads/a.mp4"

    def test_mark_failed_keeps_the_reason(self) -> None:
        video = VideoFactory.build()
        video.start_download()

        video.mark_failed("Video unavailable")

        assert video.status is VideoStatus.FAILED
        assert video.error == "Video unavailable"

    def test_each_transition_registers_that_the_video_changed(self) -> None:
        video = VideoFactory.build()

        video.start_download()
        video.mark_ready("/downloads/a.mp4")

        assert video.events == [
            VideoCreated(video),
            VideoUpdated(video),
            VideoUpdated(video),
        ]

    def test_start_download_rejects_a_video_that_is_not_pending(self) -> None:
        video = VideoFactory.build()
        video.start_download()

        with pytest.raises(InvalidStatusTransition):
            video.start_download()

    @pytest.mark.parametrize("finish", ["mark_ready", "mark_failed"])
    def test_finishing_rejects_a_video_that_is_not_downloading(
        self, finish: str
    ) -> None:
        video = VideoFactory.build()

        with pytest.raises(InvalidStatusTransition):
            getattr(video, finish)("x")

        assert video.status is VideoStatus.PENDING
        assert video.events == [VideoCreated(video)]
