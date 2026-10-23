import hashlib
from uuid import UUID, uuid7

import pytest
from fastapi.testclient import TestClient

from localreel.containers import Container
from localreel.domain.models.video import Video
from localreel.domain.types import VideoSource, VideoStatus, VideoVisibility
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
        with uow:
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

    def test_internal_address_disguised_as_youtube_is_rejected_and_not_stored(
        self, client: TestClient, container: Container
    ) -> None:
        url = "http://169.254.169.254/latest/meta-data/?youtube.com"

        response = client.post("/videos", json={"url": url, "user_id": str(uuid7())})

        assert response.status_code == 422
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        uow = container.uow()
        with uow:
            assert uow.videos.get_by_source_url_hash(url_hash) is None


def _ready_video(tags: list[str] | None = None) -> Video:
    video = VideoFactory(source=VideoSource.YOUTUBE)
    video.update_tags(tags or [])
    video.mark_downloading()
    video.mark_downloaded("v.webm")
    video.mark_transcoding()
    video.mark_ready("vid/vid.mp4", "vid/vid-thumbnail.jpg", 50, 1080, 1920)
    return video


class TestListVideos:
    def test_returns_a_ready_video_as_a_card(
        self, client: TestClient, container: Container
    ) -> None:
        uow = container.uow()
        with uow:
            video = _ready_video(tags=["music"])
            uow.videos.add(video)
            video_id = video.id

        response = client.get("/videos")

        assert response.status_code == 200
        card = response.json()["items"][0]
        assert card["id"] == str(video_id)
        assert card["playback_url"] == "/media/vid/vid.mp4"
        assert card["thumbnail_url"] == "/media/vid/vid-thumbnail.jpg"
        assert card["tags"] == ["music"]
        assert (card["width"], card["height"]) == (1080, 1920)
        assert card["saved_at"] is not None

    def test_excludes_videos_that_are_not_ready(
        self, client: TestClient, container: Container
    ) -> None:
        uow = container.uow()
        with uow:
            pending = VideoFactory()
            uow.videos.add(pending)
            pending_id = pending.id

        response = client.get("/videos", params={"limit": 100})

        assert response.status_code == 200
        ids = [card["id"] for card in response.json()["items"]]
        assert str(pending_id) not in ids

    def test_newest_first_pages_continue_from_the_cursor(
        self, client: TestClient, container: Container
    ) -> None:
        uow = container.uow()
        with uow:
            videos = [_ready_video() for _ in range(3)]
            for video in videos:
                uow.videos.add(video)
            first, second, third = (str(v.id) for v in videos)

        page_one = client.get("/videos", params={"limit": 2}).json()
        page_two = client.get(
            "/videos", params={"limit": 2, "after": page_one["next_cursor"]}
        ).json()

        assert [card["id"] for card in page_one["items"]] == [third, second]
        assert page_one["next_cursor"] == second
        assert page_two["items"][0]["id"] == first

    def test_oldest_first_ends_with_no_cursor(
        self, client: TestClient, container: Container
    ) -> None:
        uow = container.uow()
        with uow:
            videos = [_ready_video() for _ in range(3)]
            for video in videos:
                uow.videos.add(video)
            ids = [str(v.id) for v in videos]
            just_before_first = UUID(int=videos[0].id.int - 1)

        response = client.get(
            "/videos",
            params={"sort": "oldest", "after": str(just_before_first), "limit": 3},
        )

        assert response.status_code == 200
        assert [card["id"] for card in response.json()["items"]] == ids
        assert response.json()["next_cursor"] is None

    @pytest.mark.parametrize("limit", [0, 101])
    def test_rejects_a_limit_out_of_range(self, client: TestClient, limit: int) -> None:
        response = client.get("/videos", params={"limit": limit})

        assert response.status_code == 422

    def test_rejects_an_unknown_sort(self, client: TestClient) -> None:
        response = client.get("/videos", params={"sort": "popular"})

        assert response.status_code == 422


def _youtube_url() -> str:
    # A link no other test or real video uses. The tail of a UUIDv7 is random;
    # its head is the timestamp, which repeats within a millisecond.
    return f"https://youtube.com/watch?v={uuid7().hex[-11:]}"


def _saved(url: str) -> Video:
    return VideoFactory(
        source_url=url, source_url_hash=hashlib.sha256(url.encode()).hexdigest()
    )


class TestSubmitURLs:
    def test_reports_what_each_link_is_now(
        self, client: TestClient, container: Container
    ) -> None:
        new, ready_url, failed_url = _youtube_url(), _youtube_url(), _youtube_url()
        uow = container.uow()
        with uow:
            ready = _saved(ready_url)
            ready.mark_downloading()
            ready.mark_downloaded("v.webm")
            ready.mark_transcoding()
            ready.mark_ready("vid/vid.mp4", "vid/vid-thumbnail.jpg", 50, 1080, 1920)
            failed = _saved(failed_url)
            failed.mark_downloading()
            failed.mark_failed("HTTP 403")
            uow.videos.add(ready)
            uow.videos.add(failed)
            ready_id, failed_id = str(ready.id), str(failed.id)
        urls = [new, new, ready_url, failed_url, "https://vimeo.com/12345"]

        response = client.post(
            "/videos/batch",
            json={"urls": urls, "user_id": str(uuid7()), "visibility": "SHARED"},
        )

        assert response.status_code == 200
        results = response.json()
        assert [r["result"] for r in results] == [
            "queued",
            "queued",
            "ready",
            "failed",
            "unsupported",
        ]
        assert results[0]["video_id"] is not None
        assert results[1]["video_id"] == results[0]["video_id"]
        assert results[2]["video_id"] == ready_id
        assert results[3]["video_id"] == failed_id
        assert results[3]["reason"] == "HTTP 403"
        assert results[4] == {
            "url": "https://vimeo.com/12345",
            "result": "unsupported",
            "video_id": None,
            "reason": "Unsupported video source: https://vimeo.com/12345",
        }

    def test_trims_links(self, client: TestClient) -> None:
        url = _youtube_url()

        response = client.post(
            "/videos/batch", json={"urls": [f"  {url}  "], "user_id": str(uuid7())}
        )

        assert response.json()[0]["url"] == url
        assert response.json()[0]["result"] == "queued"

    @pytest.mark.parametrize("urls", [[], ["   "], [_youtube_url()] * 101])
    def test_rejects_an_empty_or_oversized_batch(
        self, client: TestClient, urls: list[str]
    ) -> None:
        response = client.post(
            "/videos/batch", json={"urls": urls, "user_id": str(uuid7())}
        )

        assert response.status_code == 422


class TestQueue:
    def test_lists_videos_still_in_the_pipeline_and_failed_ones(
        self, client: TestClient, container: Container
    ) -> None:
        uow = container.uow()
        with uow:
            pending = VideoFactory()
            failed = VideoFactory(source_url=_youtube_url())
            failed.mark_downloading()
            failed.mark_failed("HTTP 403")
            ready = _ready_video()
            for video in (pending, failed, ready):
                uow.videos.add(video)
            pending_id, failed_id, ready_id = (
                str(v.id) for v in (pending, failed, ready)
            )

        response = client.get("/videos/queue")

        assert response.status_code == 200
        by_id = {item["id"]: item for item in response.json()}
        assert by_id[pending_id]["status"] == "PENDING"
        assert by_id[failed_id]["status"] == "FAILED"
        assert by_id[failed_id]["error_message"] == "HTTP 403"
        assert ready_id not in by_id


class TestRetry:
    def test_failed_video_goes_back_to_pending(
        self, client: TestClient, container: Container
    ) -> None:
        uow = container.uow()
        with uow:
            video = VideoFactory()
            video.mark_downloading()
            video.mark_failed("HTTP 403")
            uow.videos.add(video)
            video_id = video.id

        response = client.post(f"/videos/{video_id}/retry")

        assert response.status_code == 202
        with uow:
            assert uow.videos.get(video_id).status is VideoStatus.PENDING

    def test_a_video_that_has_not_failed_is_a_conflict(
        self, client: TestClient, container: Container
    ) -> None:
        uow = container.uow()
        with uow:
            video = VideoFactory()
            uow.videos.add(video)
            video_id = video.id

        response = client.post(f"/videos/{video_id}/retry")

        assert response.status_code == 409

    def test_an_unknown_video_is_not_found(self, client: TestClient) -> None:
        response = client.post(f"/videos/{uuid7()}/retry")

        assert response.status_code == 404
