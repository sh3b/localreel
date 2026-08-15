import hashlib
from uuid import uuid7

from fastapi.testclient import TestClient

from localreel.containers import Container
from localreel.domain.types import VideoSource, VideoVisibility
from tests.factories.video import VideoFactory


class TestSubmitURL:
    URL = "https://youtube.com/watch?v=dQw4w9WgXcQ"

    def test_returns_202_and_persists_the_video(
        self, client: TestClient, container: Container
    ) -> None:
        user_id = uuid7()

        response = client.post(
            "/videos",
            json={
                "url": self.URL,
                "user_id": str(user_id),
                "visibility": VideoVisibility.SHARED.value,
            },
        )

        assert response.status_code == 202
        assert response.content == b"null"

        uow = container.uow()
        url_hash = hashlib.sha256(self.URL.encode()).hexdigest()
        video = uow.videos.get_by_source_url_hash(url_hash)
        assert video is not None
        assert video.uploaded_by == user_id

    def test_unsupported_source_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/videos",
            json={"url": "https://vimeo.com/12345", "user_id": str(uuid7())},
        )

        assert response.status_code == 422
        assert response.json() == {
            "detail": "Unsupported video source: https://vimeo.com/12345"
        }


class TestExplore:
    def test_returns_ready_videos(
        self, client: TestClient, container: Container
    ) -> None:
        uow = container.uow()
        with uow:
            video = VideoFactory(source=VideoSource.YOUTUBE)
            video.mark_downloading()
            video.mark_downloaded("v.webm")
            video.mark_transcoding()
            video.mark_ready("vid/vid.mp4", "vid/vid-thumbnail.jpg", 50, 720, 1280)
            uow.videos.add(video)
            video_id = video.id

        response = client.get("/videos/explore")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == str(video_id)
        assert data[0]["playback_path"] == "vid/vid.mp4"
        assert data[0]["thumbnail_path"] == "vid/vid-thumbnail.jpg"

    def test_excludes_non_ready_videos(
        self, client: TestClient, container: Container
    ) -> None:
        uow = container.uow()
        with uow:
            uow.videos.add(VideoFactory())

        response = client.get("/videos/explore")

        assert response.status_code == 200
        assert response.json() == []
