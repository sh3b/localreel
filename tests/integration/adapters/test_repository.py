from uuid import uuid7

import pytest
from sqlalchemy.orm import Session

from localreel.adapters.repository import PostgresVideoRepository
from localreel.containers import Container
from localreel.domain.exceptions import VideoNotFound
from localreel.domain.types import VideoStatus
from tests.factories.video import VideoFactory


class TestPostgresVideoRepository:
    URL_HASH = "a" * 64

    def test_add_then_get_round_trips(
        self, container: Container, session: Session
    ) -> None:
        repository = PostgresVideoRepository(session)
        video = VideoFactory(source_url_hash=self.URL_HASH)
        repository.add(video)
        session.commit()

        other_repository = PostgresVideoRepository(container.session_factory()())
        loaded = other_repository.get(video.id)

        assert loaded is not video
        assert loaded.id == video.id
        assert loaded.uploaded_by == video.uploaded_by
        assert loaded.source is video.source
        assert loaded.source_url == video.source_url
        assert loaded.source_url_hash == self.URL_HASH
        assert loaded.visibility is video.visibility
        assert loaded.status is VideoStatus.PENDING
        assert loaded.tags == []
        assert loaded.score == 0.0
        assert loaded.view_count == 0
        assert loaded.source_file_available is True
        assert loaded.events == []

    def test_get_unknown_id_raises(self, session: Session) -> None:
        repository = PostgresVideoRepository(session)

        with pytest.raises(VideoNotFound):
            repository.get(uuid7())

    def test_get_by_source_url_hash_returns_the_video(self, session: Session) -> None:
        repository = PostgresVideoRepository(session)
        video = VideoFactory(source_url_hash=self.URL_HASH)
        repository.add(video)
        session.commit()

        assert repository.get_by_source_url_hash(self.URL_HASH) is video

    def test_get_by_source_url_hash_miss_returns_none(self, session: Session) -> None:
        repository = PostgresVideoRepository(session)

        assert repository.get_by_source_url_hash("b" * 64) is None
