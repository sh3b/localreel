import hashlib
from uuid import UUID, uuid7

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from localreel.adapters import orm
from localreel.containers import Container
from localreel.domain.commands import SubmitURL
from localreel.domain.events import VideoIngested
from localreel.domain.exceptions import UnsupportedSource
from localreel.domain.types import VideoSource, VideoStatus, VideoVisibility
from localreel.service_layer.handlers.commands import SubmitURLHandler


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
