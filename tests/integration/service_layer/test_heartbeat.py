from datetime import UTC, datetime, timedelta
from uuid import UUID

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


class TestWorkerSweeps:
    @staticmethod
    def _stale(container: Container, *, transcoding: bool) -> UUID:
        uow = container.uow()
        with uow:
            video = VideoFactory()
            video.mark_downloading()
            if transcoding:
                video.mark_downloaded("x.webm")
                video.mark_transcoding()
            video.heartbeat_at = datetime.now(UTC) - timedelta(hours=1)
            uow.videos.add(video)
            return video.id

    @staticmethod
    def _status(container: Container, video_id: UUID) -> VideoStatus:
        uow = container.uow()
        with uow:
            return uow.videos.get(video_id).status

    def test_download_worker_sweeps_only_downloads(self, container: Container) -> None:
        downloading = self._stale(container, transcoding=False)
        transcoding = self._stale(container, transcoding=True)

        container.fail_stalled_downloads()

        assert self._status(container, downloading) is VideoStatus.FAILED
        assert self._status(container, transcoding) is VideoStatus.TRANSCODING

    def test_transcode_worker_sweeps_only_transcodes(
        self, container: Container
    ) -> None:
        downloading = self._stale(container, transcoding=False)
        transcoding = self._stale(container, transcoding=True)

        container.fail_stalled_transcodes()

        assert self._status(container, transcoding) is VideoStatus.FAILED
        assert self._status(container, downloading) is VideoStatus.DOWNLOADING
