from datetime import UTC, datetime
from uuid import uuid7

import pytest
from sqlalchemy.orm import Session

from localreel.adapters.repository import PostgresVideoRepository
from localreel.containers import Container
from localreel.domain.exceptions import VideoNotFound
from localreel.domain.types import VideoSource, VideoStatus
from localreel.domain.value_objects.source_metadata import SourceMetadata
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

    def test_source_metadata_survives_a_real_round_trip(
        self, container: Container, session: Session
    ) -> None:
        metadata = SourceMetadata(
            source_id="10000000000000001",
            title="1.2M views · 3K reactions | A Reel Caption | A Reel Uploader",
            description="A reel caption with an emoji 🥹",
            uploader="A Reel Uploader",
            uploader_id="100000000000001",
            published_at=datetime(2026, 8, 7, 9, 46, 11, tzinfo=UTC),
            view_count=1234567,
            raw={"id": "10000000000000001", "extractor": "facebook", "fps": None},
        )
        repository = PostgresVideoRepository(session)
        video = VideoFactory(source=VideoSource.FACEBOOK)
        video.mark_downloading()
        video.mark_downloaded("/downloads/v.mp4", metadata)
        repository.add(video)
        session.commit()

        other = PostgresVideoRepository(container.session_factory()())
        loaded = other.get(video.id)

        assert loaded.source_metadata == metadata

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

    def test_get_next_pending_returns_a_pending_remote_video(
        self, session: Session
    ) -> None:
        repository = PostgresVideoRepository(session)
        video = VideoFactory()
        repository.add(video)
        session.commit()

        assert repository.get_next_pending() is video

    def test_get_next_pending_none_when_nothing_pending(self, session: Session) -> None:
        repository = PostgresVideoRepository(session)

        assert repository.get_next_pending() is None

    def test_get_next_pending_excludes_local_source(self, session: Session) -> None:
        repository = PostgresVideoRepository(session)
        repository.add(VideoFactory(source=VideoSource.LOCAL))
        session.commit()

        assert repository.get_next_pending() is None

    def test_get_next_pending_excludes_non_pending_status(
        self, session: Session
    ) -> None:
        repository = PostgresVideoRepository(session)
        video = VideoFactory()
        video.mark_downloading()
        repository.add(video)
        session.commit()

        assert repository.get_next_pending() is None

    def test_get_next_downloaded_returns_a_downloaded_video(
        self, session: Session
    ) -> None:
        repository = PostgresVideoRepository(session)
        video = VideoFactory()
        video.mark_downloading()
        video.mark_downloaded("/downloads/v.webm")
        repository.add(video)
        session.commit()

        assert repository.get_next_downloaded() is video

    def test_get_next_downloaded_none_when_nothing_downloaded(
        self, session: Session
    ) -> None:
        repository = PostgresVideoRepository(session)

        assert repository.get_next_downloaded() is None

    def test_get_next_downloaded_includes_local_source(self, session: Session) -> None:
        # Unlike the download claim, LOCAL uploads must be picked up: they reach
        # DOWNLOADED directly and still need normalizing and a thumbnail.
        repository = PostgresVideoRepository(session)
        video = VideoFactory(source=VideoSource.LOCAL)
        video.mark_downloaded("/uploads/v.mp4")
        repository.add(video)
        session.commit()

        assert repository.get_next_downloaded() is video

    def test_get_next_downloaded_excludes_non_downloaded_status(
        self, session: Session
    ) -> None:
        repository = PostgresVideoRepository(session)
        repository.add(VideoFactory())
        session.commit()

        assert repository.get_next_downloaded() is None
