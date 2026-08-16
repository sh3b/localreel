import pytest
from sqlalchemy.orm import Session, sessionmaker

from localreel.adapters.orm import VideoORM
from localreel.containers import Container
from localreel.domain.events import VideoFailed
from localreel.domain.value_objects import VideoStatus
from tests.factories import VideoFactory


class TestPostgresUnitOfWork:
    def test_clean_exit_commits(
        self, container: Container, session_factory: sessionmaker[Session]
    ) -> None:
        video = VideoFactory.build()

        with container.uow() as uow:
            uow.videos.add(video)

        with session_factory() as session:
            assert session.get(VideoORM, video.id) is not None

    def test_exception_rolls_back(
        self, container: Container, session_factory: sessionmaker[Session]
    ) -> None:
        video = VideoFactory.build()

        with pytest.raises(RuntimeError), container.uow() as uow:
            uow.videos.add(video)
            raise RuntimeError("boom")

        with session_factory() as session:
            assert session.get(VideoORM, video.id) is None

    def test_commit_saves_a_video_changed_after_get(
        self, container: Container, session_factory: sessionmaker[Session]
    ) -> None:
        video = VideoFactory.build()
        with container.uow() as uow:
            uow.videos.add(video)

        with container.uow() as uow:
            uow.videos.get(video.id, lock=True).start_download()

        with session_factory() as session:
            row = session.get(VideoORM, video.id)
            assert row is not None
            assert row.status is VideoStatus.DOWNLOADING
            assert row.attempts == 1

    def test_a_second_get_keeps_the_first_change(
        self, container: Container, session_factory: sessionmaker[Session]
    ) -> None:
        video = VideoFactory.build()
        with container.uow() as uow:
            uow.videos.add(video)

        with container.uow() as uow:
            uow.videos.get(video.id, lock=True).start_download()
            again = uow.videos.get(video.id, lock=True)

            assert again.status is VideoStatus.DOWNLOADING

        with session_factory() as session:
            row = session.get(VideoORM, video.id)
            assert row is not None
            assert row.status is VideoStatus.DOWNLOADING

    def test_commit_saves_a_video_changed_after_add(
        self, container: Container, session_factory: sessionmaker[Session]
    ) -> None:
        video = VideoFactory.build()

        with container.uow() as uow:
            uow.videos.add(video)
            video.start_download()

        with session_factory() as session:
            row = session.get(VideoORM, video.id)
            assert row is not None
            assert row.status is VideoStatus.DOWNLOADING

    def test_collect_events_hands_over_the_held_videos_events_once(
        self, container: Container
    ) -> None:
        video = VideoFactory.build()
        with container.uow() as uow:
            uow.videos.add(video)

        with container.uow()(commit=False) as uow:
            loaded = uow.videos.get(video.id, lock=True)
            loaded.start_download()
            loaded.mark_failed("Video unavailable")

            assert uow.collect_events() == [VideoFailed(video.id)]
            assert uow.collect_events() == []

    def test_commit_false_rolls_back_on_exit(
        self, container: Container, session_factory: sessionmaker[Session]
    ) -> None:
        video = VideoFactory.build()

        with container.uow()(commit=False) as uow:
            uow.videos.add(video)

        with session_factory() as session:
            assert session.get(VideoORM, video.id) is None

    def test_the_next_block_commits_again_after_commit_false(
        self, container: Container, session_factory: sessionmaker[Session]
    ) -> None:
        video = VideoFactory.build()
        with container.uow()(commit=False):
            pass

        with container.uow() as uow:
            uow.videos.add(video)

        with session_factory() as session:
            assert session.get(VideoORM, video.id) is not None
