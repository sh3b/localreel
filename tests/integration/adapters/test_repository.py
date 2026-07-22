from uuid import uuid7

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from localreel.adapters import orm
from localreel.adapters.repository import (
    PostgresDownloadJobRepository,
    PostgresVideoRepository,
)
from localreel.containers import Container
from localreel.domain.entities.download_job import DownloadJob
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
        assert loaded.source_file_available is False
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


class TestPostgresDownloadJobRepository:
    def test_add_persists_the_job(self, container: Container, session: Session) -> None:
        repository = PostgresDownloadJobRepository(session)
        job = DownloadJob(id=uuid7(), video_id=uuid7())
        repository.add(job)
        session.commit()

        other_session = container.session_factory()()
        row = other_session.execute(
            select(orm.download_jobs).where(orm.download_jobs.c.id == job.id)
        ).one()

        assert row.id == job.id
        assert row.video_id == job.video_id
