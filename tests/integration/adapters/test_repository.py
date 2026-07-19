from sqlalchemy.orm import Session, sessionmaker

from localreel.adapters.orm import VideoORM
from localreel.adapters.repository import PostgresVideoRepository
from localreel.domain.types import VideoSource, VideoStatus
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
            assert row.status is VideoStatus.PENDING
