from uuid import uuid7

import pytest

from localreel.domain.events import VideoFailed
from localreel.domain.exceptions import InvalidStatusTransition
from localreel.domain.models.video import Video
from localreel.domain.value_objects import SourceURL, VideoSource, VideoStatus
from tests.factories import SourceMetadataFactory, VideoFactory


class TestCreate:
    def test_starts_pending_with_its_source(self) -> None:
        video_id = uuid7()

        video = Video.create(
            id=video_id, source_url=SourceURL.parse("https://youtu.be/jNQXAC9IVRw")
        )

        assert video.id == video_id
        assert video.source is VideoSource.YOUTUBE
        assert video.source_url == "https://youtu.be/jNQXAC9IVRw"
        assert video.source_key == "youtube:jNQXAC9IVRw"
        assert video.status is VideoStatus.PENDING
        assert video.attempts == 0


class TestDownloadTransitions:
    def test_start_download_moves_pending_to_downloading(self) -> None:
        video = VideoFactory.build()

        video.start_download()

        assert video.status is VideoStatus.DOWNLOADING
        assert video.attempts == 1

    def test_mark_ready_keeps_the_download_result(self) -> None:
        video = VideoFactory.build()
        video.start_download()
        metadata = SourceMetadataFactory.build()

        video.mark_ready(file_path="a.webm", thumbnail_path="a.webp", metadata=metadata)

        assert video.status is VideoStatus.READY
        assert video.file_path == "a.webm"
        assert video.thumbnail_path == "a.webp"
        assert video.source_metadata == metadata

    def test_mark_failed_keeps_the_reason(self) -> None:
        video = VideoFactory.build()
        video.start_download()

        video.mark_failed("Video unavailable")

        assert video.status is VideoStatus.FAILED
        assert video.error == "Video unavailable"
        assert video.events == [VideoFailed(video.id)]

    def test_a_download_that_succeeds_registers_no_event(self) -> None:
        video = VideoFactory.build()

        video.start_download()
        video.mark_ready(
            file_path="a.webm",
            thumbnail_path=None,
            metadata=SourceMetadataFactory.build(),
        )

        assert video.events == []

    def test_start_download_rejects_a_video_that_is_not_pending(self) -> None:
        video = VideoFactory.build()
        video.start_download()

        with pytest.raises(InvalidStatusTransition):
            video.start_download()

    def test_mark_ready_rejects_a_video_that_is_not_downloading(self) -> None:
        video = VideoFactory.build()

        with pytest.raises(InvalidStatusTransition):
            video.mark_ready(
                file_path="a.webm",
                thumbnail_path=None,
                metadata=SourceMetadataFactory.build(),
            )

        assert video.status is VideoStatus.PENDING
        assert video.source_metadata is None
        assert video.events == []

    def test_mark_failed_rejects_a_video_that_is_not_downloading(self) -> None:
        video = VideoFactory.build()

        with pytest.raises(InvalidStatusTransition):
            video.mark_failed("Video unavailable")

        assert video.status is VideoStatus.PENDING
        assert video.events == []


class TestResetDownload:
    def test_puts_an_interrupted_video_back_to_pending(self) -> None:
        video = VideoFactory.build()
        video.start_download()

        video.reset_download()

        assert video.status is VideoStatus.PENDING
        assert video.attempts == 1
        assert video.events == []

    def test_fails_the_video_once_its_attempts_are_used_up(self) -> None:
        video = VideoFactory.build()
        for _ in range(2):
            video.start_download()
            video.reset_download()
        video.start_download()

        video.reset_download()

        assert video.status is VideoStatus.FAILED
        assert video.error == "Download interrupted 3 times"
        assert video.events == [VideoFailed(video.id)]

    def test_rejects_a_video_that_is_not_downloading(self) -> None:
        video = VideoFactory.build()

        with pytest.raises(InvalidStatusTransition):
            video.reset_download()

        assert video.status is VideoStatus.PENDING
        assert video.events == []


class TestRetry:
    def test_puts_a_failed_video_back_to_pending_with_fresh_attempts(self) -> None:
        video = VideoFactory.build()
        for _ in range(3):
            video.start_download()
            video.reset_download()
        video.collect_events()

        video.retry()

        assert video.status is VideoStatus.PENDING
        assert video.attempts == 0
        assert video.error is None
        assert video.events == []

    def test_rejects_a_video_that_has_not_failed(self) -> None:
        video = VideoFactory.build()

        with pytest.raises(InvalidStatusTransition):
            video.retry()

        assert video.status is VideoStatus.PENDING


class TestCollectEvents:
    def test_hands_over_the_events_once(self) -> None:
        video = VideoFactory.build()
        video.start_download()
        video.mark_failed("Video unavailable")

        assert video.collect_events() == [VideoFailed(video.id)]
        assert video.collect_events() == []
