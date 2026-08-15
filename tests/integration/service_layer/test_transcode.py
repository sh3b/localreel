from uuid import UUID

from localreel.containers import Container
from localreel.domain.abstractions.transcoder import (
    AbstractTranscoder,
    TranscodeResult,
)
from localreel.domain.types import VideoStatus
from localreel.service_layer.transcode import transcode_next_downloaded
from tests.factories.video import VideoFactory


class _FakeTranscoder(AbstractTranscoder):
    def __init__(
        self, *, result: TranscodeResult | None = None, error: Exception | None = None
    ):
        self._result = result
        self._error = error

    def transcode(self, *, video_id: UUID, original_path: str) -> TranscodeResult:
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


_RESULT = TranscodeResult(
    playback_path="/media/x/x.mp4",
    thumbnail_path="/media/x/x-thumbnail.jpg",
    duration_sec=58,
    width=1080,
    height=1920,
)


class TestTranscodeNextDownloaded:
    def test_claims_transcodes_and_marks_ready(self, container: Container) -> None:
        uow = container.uow()
        with uow:
            video = VideoFactory()
            video.mark_downloading()
            video.mark_downloaded("/downloads/x.webm")
            uow.videos.add(video)
            video_id = video.id

        did_work = transcode_next_downloaded(
            uow, container.message_bus(), _FakeTranscoder(result=_RESULT)
        )

        assert did_work is True
        with uow:
            loaded = uow.videos.get(video_id)
            assert loaded.status is VideoStatus.READY
            assert loaded.playback_path == _RESULT.playback_path
            assert loaded.thumbnail_path == _RESULT.thumbnail_path
            assert loaded.duration_sec == 58
            assert (loaded.width, loaded.height) == (1080, 1920)

    def test_transcode_failure_marks_failed(self, container: Container) -> None:
        uow = container.uow()
        with uow:
            video = VideoFactory()
            video.mark_downloading()
            video.mark_downloaded("/downloads/x.webm")
            uow.videos.add(video)
            video_id = video.id

        did_work = transcode_next_downloaded(
            uow, container.message_bus(), _FakeTranscoder(error=RuntimeError("boom"))
        )

        assert did_work is True
        with uow:
            loaded = uow.videos.get(video_id)
            assert loaded.status is VideoStatus.FAILED
            assert loaded.error_message == "boom"

    def test_returns_false_when_nothing_downloaded(self, container: Container) -> None:
        uow = container.uow()

        did_work = transcode_next_downloaded(
            uow, container.message_bus(), _FakeTranscoder(result=_RESULT)
        )

        assert did_work is False
