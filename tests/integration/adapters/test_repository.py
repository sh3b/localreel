import pytest
from sqlalchemy.orm import Session, sessionmaker

from localreel.adapters.orm import VideoORM
from localreel.adapters.repository import PostgresVideoRepository
from localreel.domain.exceptions import DuplicateVideo
from localreel.domain.value_objects import VideoSource, VideoStatus
from tests.factories import VideoFactory


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

    def test_exists_finds_a_video_by_its_source_key(self, session: Session) -> None:
        repository = PostgresVideoRepository(session)
        repository.add(VideoFactory.build(source_url="https://youtu.be/jNQXAC9IVRw"))

        assert repository.exists(source_key="youtube:jNQXAC9IVRw")
        assert not repository.exists(source_key="youtube:aqz-KE-bpKQ")
