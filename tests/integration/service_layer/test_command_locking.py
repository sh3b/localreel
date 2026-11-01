import threading
from collections.abc import Callable, Iterator
from uuid import UUID

import pytest
from sqlalchemy import Engine, delete
from sqlalchemy.orm import Session

from localreel.adapters.orm import VideoORM
from localreel.containers import Container
from localreel.domain.commands import (
    MarkFailed,
    MarkReady,
    RemoveVideo,
    ResetDownload,
    RetryVideo,
)
from localreel.domain.exceptions import InvalidStatusTransition
from localreel.domain.value_objects import VideoStatus
from tests.factories import SourceMetadataFactory, VideoFactory


class TestCommandLocking:
    """Two transactions must really commit here, so these tests skip the
    rolled-back test transaction and delete their row afterwards."""

    @pytest.fixture
    def committing_container(self, engine: Engine) -> Iterator[Container]:
        container = Container()
        with container.engine.override(engine):
            yield container

    @pytest.fixture
    def video_in(self, engine: Engine) -> Iterator[Callable[[VideoStatus], UUID]]:
        video = VideoFactory.build()

        def insert(status: VideoStatus) -> UUID:
            with Session(engine) as session, session.begin():
                session.add(
                    VideoORM(
                        id=video.id,
                        source=video.source,
                        source_url=video.source_url,
                        source_key=video.source_key,
                        status=status,
                    )
                )
            return video.id

        yield insert
        with Session(engine) as session, session.begin():
            session.execute(delete(VideoORM).where(VideoORM.id == video.id))

    @pytest.mark.parametrize(
        ("status", "make_command"),
        [
            (
                VideoStatus.DOWNLOADING,
                lambda video_id: MarkReady(
                    video_id=video_id,
                    file_path="a.webm",
                    thumbnail_path=None,
                    metadata=SourceMetadataFactory.build(),
                ),
            ),
            (
                VideoStatus.DOWNLOADING,
                lambda video_id: MarkFailed(video_id=video_id, reason="unavailable"),
            ),
            (
                VideoStatus.DOWNLOADING,
                lambda video_id: ResetDownload(video_id=video_id),
            ),
            (
                VideoStatus.FAILED,
                lambda video_id: RetryVideo(video_id=video_id),
            ),
        ],
        ids=["MarkReady", "MarkFailed", "ResetDownload", "RetryVideo"],
    )
    def test_reads_the_status_a_concurrent_change_left_and_refuses(
        self,
        committing_container: Container,
        video_in: Callable[[VideoStatus], UUID],
        engine: Engine,
        status: VideoStatus,
        make_command: Callable[
            [UUID], MarkReady | MarkFailed | ResetDownload | RetryVideo
        ],
    ) -> None:
        container = committing_container
        video_id = video_in(status)
        command = make_command(video_id)
        errors: list[Exception] = []

        def send() -> None:
            try:
                with container.uow():
                    container.message_bus().handle(command)
            except Exception as exc:
                errors.append(exc)

        with Session(engine) as other, other.begin():
            row = other.get_one(VideoORM, video_id, with_for_update=True)
            sender = threading.Thread(target=send)
            sender.start()
            sender.join(timeout=0.5)
            row.status = VideoStatus.PENDING

        sender.join(timeout=5)
        assert not sender.is_alive()
        assert len(errors) == 1
        assert isinstance(errors[0], InvalidStatusTransition)
        with Session(engine) as session:
            assert session.get_one(VideoORM, video_id).status is VideoStatus.PENDING

    def test_remove_waits_for_a_claim_and_refuses_the_claimed_video(
        self,
        committing_container: Container,
        video_in: Callable[[VideoStatus], UUID],
        engine: Engine,
    ) -> None:
        container = committing_container
        video_id = video_in(VideoStatus.PENDING)
        errors: list[Exception] = []

        def send() -> None:
            try:
                with container.uow():
                    container.message_bus().handle(RemoveVideo(video_id=video_id))
            except Exception as exc:
                errors.append(exc)

        with Session(engine) as worker, worker.begin():
            row = worker.get_one(VideoORM, video_id, with_for_update=True)
            sender = threading.Thread(target=send)
            sender.start()
            sender.join(timeout=0.5)
            row.status = VideoStatus.DOWNLOADING

        sender.join(timeout=5)
        assert not sender.is_alive()
        assert len(errors) == 1
        assert isinstance(errors[0], InvalidStatusTransition)
        with Session(engine) as session:
            assert session.get_one(VideoORM, video_id).status is VideoStatus.DOWNLOADING
