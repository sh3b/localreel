from uuid import uuid7

import pytest
from sqlalchemy.orm import Session, sessionmaker

from localreel.adapters.orm import VideoORM
from localreel.adapters.repository import PostgresVideoRepository
from localreel.domain.exceptions import DuplicateVideo, VideoNotFound
from localreel.domain.value_objects import VideoSource, VideoStatus
from tests.factories import SourceMetadataFactory, VideoFactory


class TestPostgresVideoRepository:
    def test_add_persists_the_video(
        self, session: Session, session_factory: sessionmaker[Session]
    ) -> None:
        video = VideoFactory.build(source_url="https://youtu.be/jNQXAC9IVRw")
        PostgresVideoRepository(session).add(video)
        session.commit()

        with session_factory() as other_session:
            row = other_session.get(VideoORM, video.id)

            assert row is not None
            assert row.source is VideoSource.YOUTUBE
            assert row.source_url == "https://youtu.be/jNQXAC9IVRw"
            assert row.source_key == "youtube:jNQXAC9IVRw"
            assert row.status is VideoStatus.PENDING

    def test_add_rejects_a_known_source_key(self, session: Session) -> None:
        repository = PostgresVideoRepository(session)
        repository.add(VideoFactory.build(source_url="https://youtu.be/jNQXAC9IVRw"))

        with pytest.raises(DuplicateVideo):
            repository.add(
                VideoFactory.build(source_url="https://youtube.com/watch?v=jNQXAC9IVRw")
            )

    def test_add_accepts_a_link_whose_video_was_removed(self, session: Session) -> None:
        repository = PostgresVideoRepository(session)
        removed = VideoFactory.build(source_url="https://youtu.be/jNQXAC9IVRw")
        repository.add(removed)
        removed.remove()
        repository.save(removed)
        again = VideoFactory.build(source_url="https://youtu.be/jNQXAC9IVRw")

        repository.add(again)

        assert repository.get(again.id, lock=False).status is VideoStatus.PENDING

    def test_exists_ignores_a_removed_video(self, session: Session) -> None:
        repository = PostgresVideoRepository(session)
        video = VideoFactory.build(source_url="https://youtu.be/jNQXAC9IVRw")
        repository.add(video)
        video.remove()
        repository.save(video)
        session.flush()

        assert not repository.exists(source_key="youtube:jNQXAC9IVRw")

    def test_exists_finds_a_video_by_its_source_key(self, session: Session) -> None:
        repository = PostgresVideoRepository(session)
        repository.add(VideoFactory.build(source_url="https://youtu.be/jNQXAC9IVRw"))

        assert repository.exists(source_key="youtube:jNQXAC9IVRw")
        assert not repository.exists(source_key="youtube:aqz-KE-bpKQ")

    def test_get_returns_the_stored_video(self, session: Session) -> None:
        repository = PostgresVideoRepository(session)
        video = VideoFactory.build(source_url="https://youtu.be/jNQXAC9IVRw")
        repository.add(video)

        loaded = repository.get(video.id, lock=False)

        assert loaded.id == video.id
        assert loaded.source_key == "youtube:jNQXAC9IVRw"
        assert loaded.status is VideoStatus.PENDING
        assert loaded.file_path is None
        assert loaded.error is None

    def test_get_raises_for_an_unknown_id(self, session: Session) -> None:
        with pytest.raises(VideoNotFound):
            PostgresVideoRepository(session).get(uuid7(), lock=False)

    def test_save_writes_the_changes(
        self, session: Session, session_factory: sessionmaker[Session]
    ) -> None:
        repository = PostgresVideoRepository(session)
        video = VideoFactory.build()
        repository.add(video)
        video.start_download()
        metadata = SourceMetadataFactory.build()
        video.mark_ready(file_path="a.webm", thumbnail_path="a.webp", metadata=metadata)

        repository.save(video)
        session.commit()

        with session_factory() as other_session:
            loaded = PostgresVideoRepository(other_session).get(video.id, lock=False)
            assert loaded.status is VideoStatus.READY
            assert loaded.attempts == 1
            assert loaded.file_path == "a.webm"
            assert loaded.thumbnail_path == "a.webp"
            assert loaded.source_metadata == metadata

    def test_next_pending_returns_the_oldest_pending_video(
        self, session: Session
    ) -> None:
        repository = PostgresVideoRepository(session)
        started = VideoFactory.build(source_url="https://youtu.be/jNQXAC9IVRw")
        older = VideoFactory.build(source_url="https://youtu.be/dQw4w9WgXcQ")
        newer = VideoFactory.build(source_url="https://youtu.be/9bZkp7q19f0")
        for video in (newer, started, older):
            repository.add(video)
        started.start_download()
        repository.save(started)

        assert repository.next_pending() == older.id

    def test_next_pending_is_none_without_pending_videos(
        self, session: Session
    ) -> None:
        assert PostgresVideoRepository(session).next_pending() is None

    def test_downloading_returns_every_downloading_video(
        self, session: Session
    ) -> None:
        repository = PostgresVideoRepository(session)
        pending = VideoFactory.build(source_url="https://youtu.be/jNQXAC9IVRw")
        first = VideoFactory.build(source_url="https://youtu.be/dQw4w9WgXcQ")
        second = VideoFactory.build(source_url="https://youtu.be/9bZkp7q19f0")
        for video in (pending, first, second):
            repository.add(video)
        for video in (first, second):
            video.start_download()
            repository.save(video)

        assert set(repository.downloading()) == {first.id, second.id}

    def test_removed_returns_every_removed_video(self, session: Session) -> None:
        repository = PostgresVideoRepository(session)
        kept = VideoFactory.build(source_url="https://youtu.be/jNQXAC9IVRw")
        removed = VideoFactory.build(source_url="https://youtu.be/dQw4w9WgXcQ")
        for video in (kept, removed):
            repository.add(video)
        removed.remove()
        repository.save(removed)

        assert repository.removed() == [removed.id]
