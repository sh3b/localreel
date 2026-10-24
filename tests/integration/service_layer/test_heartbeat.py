from datetime import UTC, datetime, timedelta

from localreel.containers import Container
from localreel.domain.types import VideoStatus
from localreel.service_layer.heartbeat import fail_stalled
from tests.factories.video import VideoFactory

_STALLED_AFTER_SEC = 120.0


class TestFailStalled:
    def test_marks_a_video_with_stopped_beats_failed(
        self, container: Container
    ) -> None:
        uow = container.uow()
        with uow:
            video = VideoFactory()
            video.mark_downloading()
            video.heartbeat_at = datetime.now(UTC) - timedelta(minutes=10)
            uow.videos.add(video)
            video_id = video.id

        fail_stalled(
            uow, container.message_bus(), VideoStatus.DOWNLOADING, _STALLED_AFTER_SEC
        )

        with uow:
            loaded = uow.videos.get(video_id)
            assert loaded.status is VideoStatus.FAILED
            assert loaded.error_message == "worker stalled"
            assert loaded.heartbeat_at is None

    def test_leaves_a_beating_video_alone(self, container: Container) -> None:
        uow = container.uow()
        with uow:
            video = VideoFactory()
            video.mark_downloading()
            uow.videos.add(video)
            video_id = video.id

        fail_stalled(
            uow, container.message_bus(), VideoStatus.DOWNLOADING, _STALLED_AFTER_SEC
        )

        with uow:
            assert uow.videos.get(video_id).status is VideoStatus.DOWNLOADING

    def test_sweeps_only_the_status_it_is_given(self, container: Container) -> None:
        uow = container.uow()
        with uow:
            video = VideoFactory()
            video.mark_downloading()
            video.heartbeat_at = datetime.now(UTC) - timedelta(minutes=10)
            uow.videos.add(video)
            video_id = video.id

        fail_stalled(
            uow, container.message_bus(), VideoStatus.TRANSCODING, _STALLED_AFTER_SEC
        )

        with uow:
            assert uow.videos.get(video_id).status is VideoStatus.DOWNLOADING
