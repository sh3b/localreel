import hashlib
from uuid import uuid7

from fastapi.testclient import TestClient

from localreel.containers import Container
from localreel.domain.types import VideoVisibility


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
