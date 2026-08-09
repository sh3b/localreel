import hashlib
from uuid import UUID, uuid7

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from localreel.adapters import orm
from localreel.containers import Container
from localreel.domain.commands import MarkDownloaded, MarkFailed, SubmitURL
from localreel.domain.events import VideoDownloaded, VideoFailed, VideoIngested
from localreel.domain.exceptions import UnsupportedSource
from localreel.domain.types import VideoSource, VideoStatus, VideoVisibility
from localreel.service_layer.handlers.commands import (
    MarkDownloadedHandler,
    MarkFailedHandler,
    SubmitURLHandler,
)
from tests.factories.video import VideoFactory


class TestSubmitURL:
    URL = "https://youtube.com/watch?v=dQw4w9WgXcQ"

    def test_persists_a_pending_video(self, container: Container) -> None:
        uow = container.uow()
        user_id = uuid7()

        with uow:
            container.message_bus().handle(
                SubmitURL(
                    url=self.URL, user_id=user_id, visibility=VideoVisibility.SHARED
                )
            )

        url_hash = hashlib.sha256(self.URL.encode()).hexdigest()
        video = uow.videos.get_by_source_url_hash(url_hash)
        assert video is not None
        assert video.uploaded_by == user_id
        assert video.status is VideoStatus.PENDING
        assert video.source is VideoSource.YOUTUBE
        assert video.source_url == self.URL
        assert video.visibility is VideoVisibility.SHARED

    def test_resubmitting_the_same_url_creates_no_second_video(
        self, container: Container, session: Session
    ) -> None:
        uow = container.uow()
        bus = container.message_bus()

        with uow:
            bus.handle(
                SubmitURL(
                    url=self.URL, user_id=UUID(int=0), visibility=VideoVisibility.SHARED
                )
            )
        with uow:
            bus.handle(
                SubmitURL(
                    url=self.URL,
                    user_id=UUID(int=0),
                    visibility=VideoVisibility.PRIVATE,
                )
            )

        count = session.scalar(select(func.count()).select_from(orm.videos))
        assert count == 1

    def test_unsupported_url_raises_and_persists_nothing(
        self, container: Container, session: Session
    ) -> None:
        uow = container.uow()
        bus = container.message_bus()

        with pytest.raises(UnsupportedSource):
            with uow:
                bus.handle(
                    SubmitURL(
                        url="https://vimeo.com/12345",
                        user_id=UUID(int=0),
                        visibility=VideoVisibility.SHARED,
                    )
                )

        count = session.scalar(select(func.count()).select_from(orm.videos))
        assert count == 0

    def test_returns_video_ingested_when_created(self, container: Container) -> None:
        uow = container.uow()
        handler = SubmitURLHandler(uow)
        cmd = SubmitURL(
            url=self.URL, user_id=uuid7(), visibility=VideoVisibility.SHARED
        )

        with uow:
            events = handler(cmd)

        url_hash = hashlib.sha256(self.URL.encode()).hexdigest()
        video = uow.videos.get_by_source_url_hash(url_hash)
        assert video is not None
        assert events == [VideoIngested(video_id=video.id)]

    def test_returns_no_events_on_duplicate(self, container: Container) -> None:
        uow = container.uow()
        handler = SubmitURLHandler(uow)
        cmd = SubmitURL(
            url=self.URL, user_id=uuid7(), visibility=VideoVisibility.SHARED
        )

        with uow:
            handler(cmd)
        with uow:
            events = handler(cmd)

        assert events == []


class TestMarkDownloaded:
    def test_persists_downloaded_state(self, container: Container) -> None:
        uow = container.uow()
        with uow:
            video = VideoFactory()
            video.mark_downloading()
            uow.videos.add(video)
            video_id = video.id

        with uow:
            container.message_bus().handle(
                MarkDownloaded(video_id=video_id, original_path="/data/x.mp4")
            )

        with uow:
            loaded = uow.videos.get(video_id)
            assert loaded.status is VideoStatus.DOWNLOADED
            assert loaded.original_path == "/data/x.mp4"
            assert loaded.source_file_available is True

    def test_returns_video_downloaded_event(self, container: Container) -> None:
        uow = container.uow()
        handler = MarkDownloadedHandler(uow)
        with uow:
            video = VideoFactory()
            video.mark_downloading()
            uow.videos.add(video)
            video_id = video.id

        with uow:
            events = handler(
                MarkDownloaded(video_id=video_id, original_path="/data/x.mp4")
            )

        assert events == [VideoDownloaded(video_id=video_id)]


class TestMarkFailed:
    def test_persists_failed_state(self, container: Container) -> None:
        uow = container.uow()
        with uow:
            video = VideoFactory()
            video.mark_downloading()
            uow.videos.add(video)
            video_id = video.id

        with uow:
            container.message_bus().handle(MarkFailed(video_id=video_id, reason="boom"))

        with uow:
            loaded = uow.videos.get(video_id)
            assert loaded.status is VideoStatus.FAILED
            assert loaded.error_message == "boom"

    def test_returns_video_failed_event(self, container: Container) -> None:
        uow = container.uow()
        handler = MarkFailedHandler(uow)
        with uow:
            video = VideoFactory()
            video.mark_downloading()
            uow.videos.add(video)
            video_id = video.id

        with uow:
            events = handler(MarkFailed(video_id=video_id, reason="boom"))

        assert events == [VideoFailed(video_id=video_id, reason="boom")]
