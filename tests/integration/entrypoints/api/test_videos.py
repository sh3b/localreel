import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from localreel.adapters.orm import VideoORM
from localreel.adapters.repository import PostgresVideoRepository
from localreel.domain.value_objects import VideoStatus
from tests.factories import SourceMetadataFactory, VideoFactory


class TestSubmitURL:
    def test_returns_202_and_persists_a_pending_video(
        self, client: TestClient, session: Session
    ) -> None:
        response = client.post("/videos", json={"url": "https://youtu.be/jNQXAC9IVRw"})

        assert response.status_code == 202
        row = session.scalars(select(VideoORM)).one()
        assert row.source_key == "youtube:jNQXAC9IVRw"
        assert row.status is VideoStatus.PENDING

    def test_resubmitting_returns_202_and_keeps_one_row(
        self, client: TestClient, session: Session
    ) -> None:
        for url in (
            "https://youtu.be/jNQXAC9IVRw",
            "https://youtube.com/watch?v=jNQXAC9IVRw",
        ):
            assert client.post("/videos", json={"url": url}).status_code == 202

        assert len(session.scalars(select(VideoORM)).all()) == 1

    def test_losing_a_race_to_the_same_video_returns_202_and_keeps_one_row(
        self, client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client.post("/videos", json={"url": "https://youtu.be/jNQXAC9IVRw"})
        monkeypatch.setattr(PostgresVideoRepository, "exists", lambda *_, **__: False)

        response = client.post("/videos", json={"url": "https://youtu.be/jNQXAC9IVRw"})

        assert response.status_code == 202
        assert len(session.scalars(select(VideoORM)).all()) == 1

    def test_unsupported_source_returns_422_and_persists_nothing(
        self, client: TestClient, session: Session
    ) -> None:
        response = client.post("/videos", json={"url": "https://vimeo.com/12345"})

        assert response.status_code == 422
        assert response.json() == {
            "detail": "Unsupported video source: https://vimeo.com/12345"
        }
        assert session.scalars(select(VideoORM)).all() == []


class TestListVideos:
    def test_returns_the_ready_videos_as_cards(
        self, client: TestClient, session: Session
    ) -> None:
        repository = PostgresVideoRepository(session)
        video = VideoFactory.build(source_url="https://youtu.be/jNQXAC9IVRw")
        repository.add(video)
        video.start_download()
        video.mark_ready(
            file_path=f"{video.id}.webm",
            thumbnail_path=f"{video.id}.webp",
            metadata=SourceMetadataFactory.build(),
        )
        repository.save(video)
        session.commit()

        response = client.get("/videos")

        assert response.status_code == 200
        [card] = response.json()
        assert card["id"] == str(video.id)
        assert card["title"] == "Me at the zoo"
        assert card["source"] == "YOUTUBE"
        assert card["playback_url"] == f"/media/{video.id}.webm"

    def test_returns_an_empty_list_without_ready_videos(
        self, client: TestClient
    ) -> None:
        response = client.get("/videos")

        assert response.status_code == 200
        assert response.json() == []
