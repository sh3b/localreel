import threading
from collections.abc import Callable, Iterator
from uuid import UUID

import pytest
from sqlalchemy import Engine, delete
from sqlalchemy.orm import Session

from localreel.adapters.orm import VideoORM
from localreel.containers import Container
from localreel.domain.commands import MarkFailed, MarkReady, ResetDownload
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
    def downloading_video_id(self, engine: Engine) -> Iterator[UUID]:
        video = VideoFactory.build()
        with Session(engine) as session, session.begin():
            session.add(
                VideoORM(
                    id=video.id,
                    source=video.source,
                    source_url=video.source_url,
                    source_key=video.source_key,
                    status=VideoStatus.DOWNLOADING,
                )
            )
        yield video.id
        with Session(engine) as session, session.begin():
            session.execute(delete(VideoORM).where(VideoORM.id == video.id))

    @pytest.mark.parametrize(
        "make_command",
        [
            lambda video_id: MarkReady(
                video_id=video_id,
                file_path="a.webm",
                thumbnail_path=None,
                metadata=SourceMetadataFactory.build(),
            ),
            lambda video_id: MarkFailed(video_id=video_id, reason="unavailable"),
            lambda video_id: ResetDownload(video_id=video_id),
        ],
        ids=["MarkReady", "MarkFailed", "ResetDownload"],
    )
    def test_reads_the_status_a_concurrent_change_left_and_refuses(
        self,
        committing_container: Container,
        downloading_video_id: UUID,
        engine: Engine,
        make_command: Callable[[UUID], MarkReady | MarkFailed | ResetDownload],
    ) -> None:
        container = committing_container
        command = make_command(downloading_video_id)
        errors: list[Exception] = []

        def send() -> None:
            try:
                with container.uow():
                    container.message_bus().handle(command)
            except Exception as exc:
                errors.append(exc)

        with Session(engine) as other, other.begin():
            row = other.get_one(VideoORM, downloading_video_id, with_for_update=True)
            sender = threading.Thread(target=send)
            sender.start()
            sender.join(timeout=0.5)
            row.status = VideoStatus.PENDING

        sender.join(timeout=5)
        assert not sender.is_alive()
        assert len(errors) == 1
        assert isinstance(errors[0], InvalidStatusTransition)
        with Session(engine) as session:
            assert (
                session.get_one(VideoORM, downloading_video_id).status
                is VideoStatus.PENDING
            )
