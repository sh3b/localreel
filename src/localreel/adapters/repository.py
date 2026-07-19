from sqlalchemy.orm import Session

from localreel.adapters.orm import VideoORM
from localreel.domain.models.video import Video
from localreel.domain.repository import AbstractVideoRepository


class PostgresVideoRepository(AbstractVideoRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, video: Video) -> None:
        self._session.add(_to_orm(video))


def _to_orm(video: Video) -> VideoORM:
    return VideoORM(
        id=video.id,
        source=video.source,
        source_url=video.source_url,
        status=video.status,
    )
