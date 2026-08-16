import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from localreel.adapters.orm import VideoORM
from localreel.adapters.repository import PostgresVideoRepository
from localreel.domain.models.video import Video
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
        video = self._ready(session, "https://youtu.be/jNQXAC9IVRw")

        response = client.get("/videos")

        assert response.status_code == 200
        page = response.json()
        assert page["next_cursor"] is None
        [card] = page["items"]
        assert card["id"] == str(video.id)
        assert card["title"] == "Me at the zoo"
        assert card["source"] == "YOUTUBE"
        assert card["playback_url"] == f"/media/{video.id}.webm"

    def test_returns_an_empty_page_without_ready_videos(
        self, client: TestClient
    ) -> None:
        response = client.get("/videos")

        assert response.status_code == 200
        assert response.json() == {"items": [], "next_cursor": None}

    @pytest.mark.parametrize("limit", [0, 101])
    def test_rejects_a_limit_out_of_range(self, client: TestClient, limit: int) -> None:
        response = client.get("/videos", params={"limit": limit})

        assert response.status_code == 422

    def test_pages_through_with_sort_cursor_and_limit(
        self, client: TestClient, session: Session
    ) -> None:
        older = self._ready(session, "https://youtu.be/jNQXAC9IVRw")
        newer = self._ready(session, "https://youtu.be/dQw4w9WgXcQ")

        first = client.get("/videos", params={"sort": "oldest", "limit": 1}).json()
        second = client.get(
            "/videos",
            params={"sort": "oldest", "limit": 1, "after": first["next_cursor"]},
        ).json()

        assert [card["id"] for card in first["items"]] == [str(older.id)]
        assert first["next_cursor"] == str(older.id)
        assert [card["id"] for card in second["items"]] == [str(newer.id)]
        assert second["next_cursor"] is None

    @staticmethod
    def _ready(session: Session, source_url: str) -> Video:
        repository = PostgresVideoRepository(session)
        video = VideoFactory.build(source_url=source_url)
        repository.add(video)
        video.start_download()
        video.mark_ready(
            file_path=f"{video.id}.webm",
            thumbnail_path=f"{video.id}.webp",
            metadata=SourceMetadataFactory.build(),
        )
        repository.save(video)
        session.commit()
        return video
