from uuid import UUID

import pytest

from localreel.containers import Container
from localreel.domain.abstractions.transcoder import (
    AbstractTranscoder,
    TranscodeResult,
)
from localreel.domain.commands import MarkFailed
from localreel.domain.types import VideoStatus
from localreel.service_layer.transcode import transcode_next_downloaded
from tests.factories.video import VideoFactory


class _FakeTranscoder(AbstractTranscoder):
    def __init__(
        self,
        *,
        result: TranscodeResult | None = None,
        error: BaseException | None = None,
    ):
        self._result = result
        self._error = error

    def transcode(self, *, video_id: UUID, original_path: str) -> TranscodeResult:
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


# Longer than any test, so no beat fires: a second thread would share the
# test's single connection.
_HEARTBEAT_SEC = 3600.0

_RESULT = TranscodeResult(
    playback_path="x/x.mp4",
    thumbnail_path="x/x-thumbnail.jpg",
    duration_sec=58,
    width=1080,
    height=1920,
)


class _SweptMidTranscode(AbstractTranscoder):
    """Has the sweep fail the video while the transcode runs."""

    def __init__(self, container: Container) -> None:
        self._container = container

    def transcode(self, *, video_id: UUID, original_path: str) -> TranscodeResult:
        with self._container.uow():
            self._container.message_bus().handle(
                MarkFailed(video_id=video_id, reason="worker stalled")
            )
        return _RESULT


class TestTranscodeNextDownloaded:
    def test_claims_transcodes_and_marks_ready(self, container: Container) -> None:
        uow = container.uow()
        with uow:
            video = VideoFactory()
            video.mark_downloading()
            video.mark_downloaded("x.webm")
            uow.videos.add(video)
            video_id = video.id

        did_work = transcode_next_downloaded(
            uow,
            container.message_bus(),
            _FakeTranscoder(result=_RESULT),
            "/downloads",
            _HEARTBEAT_SEC,
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
            video.mark_downloaded("x.webm")
            uow.videos.add(video)
            video_id = video.id

        did_work = transcode_next_downloaded(
            uow,
            container.message_bus(),
            _FakeTranscoder(error=RuntimeError("boom")),
            "/downloads",
            _HEARTBEAT_SEC,
        )

        assert did_work is True
        with uow:
            loaded = uow.videos.get(video_id)
            assert loaded.status is VideoStatus.FAILED
            assert loaded.error_message == "boom"

    @pytest.mark.parametrize("interruption", [SystemExit(143), KeyboardInterrupt()])
    def test_interrupted_transcode_marks_failed_and_propagates(
        self, container: Container, interruption: BaseException
    ) -> None:
        uow = container.uow()
        with uow:
            video = VideoFactory()
            video.mark_downloading()
            video.mark_downloaded("x.webm")
            uow.videos.add(video)
            video_id = video.id

        with pytest.raises(type(interruption)):
            transcode_next_downloaded(
                uow,
                container.message_bus(),
                _FakeTranscoder(error=interruption),
                "/downloads",
                _HEARTBEAT_SEC,
            )

        with uow:
            loaded = uow.videos.get(video_id)
            assert loaded.status is VideoStatus.FAILED
            assert loaded.error_message == "worker shut down"

    def test_returns_false_when_nothing_downloaded(self, container: Container) -> None:
        uow = container.uow()

        did_work = transcode_next_downloaded(
            uow,
            container.message_bus(),
            _FakeTranscoder(result=_RESULT),
            "/downloads",
            _HEARTBEAT_SEC,
        )

        assert did_work is False

    def test_outcome_after_a_sweep_is_dropped(self, container: Container) -> None:
        uow = container.uow()
        with uow:
            video = VideoFactory()
            video.mark_downloading()
            video.mark_downloaded("x.webm")
            uow.videos.add(video)
            video_id = video.id

        did_work = transcode_next_downloaded(
            uow,
            container.message_bus(),
            _SweptMidTranscode(container),
            "/downloads",
            _HEARTBEAT_SEC,
        )

        assert did_work is True
        with uow:
            loaded = uow.videos.get(video_id)
            assert loaded.status is VideoStatus.FAILED
            assert loaded.error_message == "worker stalled"
