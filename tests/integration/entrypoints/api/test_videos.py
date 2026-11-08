from uuid import uuid7

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


class TestSubmitURLs:
    def test_saves_new_links_and_reports_them_queued(
        self, client: TestClient, session: Session
    ) -> None:
        urls = [
            "https://youtu.be/jNQXAC9IVRw",
            "https://youtube.com/watch?v=jNQXAC9IVRw",
            "https://youtu.be/dQw4w9WgXcQ",
        ]

        response = client.post("/videos/batch", json={"urls": urls})

        assert response.status_code == 200
        results = response.json()
        assert [r["url"] for r in results] == urls
        assert [r["result"] for r in results] == ["queued"] * 3
        assert results[0]["video_id"] == results[1]["video_id"]
        rows = session.scalars(select(VideoORM)).all()
        assert {str(row.id) for row in rows} == {r["video_id"] for r in results}

    def test_saves_a_link_again_after_its_video_was_removed(
        self, client: TestClient, session: Session
    ) -> None:
        removed = VideoFactory.build(source_url="https://youtu.be/jNQXAC9IVRw")
        PostgresVideoRepository(session).add(removed)
        session.commit()
        client.delete(f"/videos/{removed.id}")

        response = client.post(
            "/videos/batch", json={"urls": ["https://youtu.be/jNQXAC9IVRw"]}
        )

        [result] = response.json()
        assert result["result"] == "queued"
        assert result["video_id"] != str(removed.id)

    @pytest.mark.parametrize(
        ("status", "result"),
        [
            (VideoStatus.PENDING, "queued"),
            (VideoStatus.DOWNLOADING, "queued"),
            (VideoStatus.READY, "ready"),
            (VideoStatus.FAILED, "failed"),
        ],
    )
    def test_reports_a_saved_video_by_its_status(
        self, client: TestClient, session: Session, status: VideoStatus, result: str
    ) -> None:
        video = VideoFactory.build(source_url="https://youtu.be/jNQXAC9IVRw")
        repository = PostgresVideoRepository(session)
        repository.add(video)
        if status is not VideoStatus.PENDING:
            video.start_download()
        if status is VideoStatus.READY:
            video.mark_ready(
                file_path="a.webm",
                thumbnail_path=None,
                metadata=SourceMetadataFactory.build(),
            )
        if status is VideoStatus.FAILED:
            video.mark_failed("Video unavailable")
        repository.save(video)
        session.commit()

        response = client.post(
            "/videos/batch", json={"urls": ["https://youtu.be/jNQXAC9IVRw"]}
        )

        [link] = response.json()
        assert link["result"] == result
        assert link["video_id"] == str(video.id)
        assert link["reason"] == video.error

    def test_reports_an_unsupported_link_and_saves_the_others(
        self, client: TestClient, session: Session
    ) -> None:
        response = client.post(
            "/videos/batch",
            json={"urls": ["https://vimeo.com/12345", "https://youtu.be/jNQXAC9IVRw"]},
        )

        unsupported, saved = response.json()
        assert unsupported == {
            "url": "https://vimeo.com/12345",
            "result": "unsupported",
            "video_id": None,
            "reason": "Unsupported video source: https://vimeo.com/12345",
        }
        assert saved["result"] == "queued"
        row = session.scalars(select(VideoORM)).one()
        assert row.source_key == "youtube:jNQXAC9IVRw"

    def test_reports_a_link_lost_to_a_race_and_saves_the_others(
        self, client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        video = VideoFactory.build(source_url="https://youtu.be/jNQXAC9IVRw")
        PostgresVideoRepository(session).add(video)
        session.commit()
        monkeypatch.setattr(PostgresVideoRepository, "exists", lambda *_, **__: False)

        response = client.post(
            "/videos/batch",
            json={
                "urls": ["https://youtu.be/jNQXAC9IVRw", "https://youtu.be/dQw4w9WgXcQ"]
            },
        )

        assert response.status_code == 200
        lost, saved = response.json()
        assert lost["result"] == "queued"
        assert lost["video_id"] == str(video.id)
        assert saved["result"] == "queued"
        assert len(session.scalars(select(VideoORM)).all()) == 2

    @pytest.mark.parametrize(
        "urls",
        [[], ["https://youtu.be/jNQXAC9IVRw"] * 101, ["   "]],
        ids=["empty", "too-many", "blank"],
    )
    def test_rejects_a_batch_out_of_bounds(
        self, client: TestClient, session: Session, urls: list[str]
    ) -> None:
        response = client.post("/videos/batch", json={"urls": urls})

        assert response.status_code == 422
        assert session.scalars(select(VideoORM)).all() == []


class TestRetryVideo:
    def test_returns_202_and_puts_a_failed_video_back_to_pending(
        self, client: TestClient, session: Session
    ) -> None:
        repository = PostgresVideoRepository(session)
        video = VideoFactory.build()
        repository.add(video)
        video.start_download()
        video.mark_failed("Video unavailable")
        repository.save(video)
        session.commit()

        response = client.post(f"/videos/{video.id}/retry")

        assert response.status_code == 202
        session.expire_all()
        assert session.get_one(VideoORM, video.id).status is VideoStatus.PENDING

    def test_an_unknown_video_returns_404(self, client: TestClient) -> None:
        video_id = uuid7()

        response = client.post(f"/videos/{video_id}/retry")

        assert response.status_code == 404
        assert response.json() == {"detail": f"Video {video_id} not found"}

    def test_a_video_that_has_not_failed_returns_409(
        self, client: TestClient, session: Session
    ) -> None:
        video = VideoFactory.build()
        PostgresVideoRepository(session).add(video)
        session.commit()

        response = client.post(f"/videos/{video.id}/retry")

        assert response.status_code == 409
        assert response.json() == {
            "detail": f"Video {video.id} is PENDING, expected FAILED; "
            "cannot become PENDING"
        }


class TestRetryFailedVideos:
    def test_returns_202_and_puts_every_failed_video_back_to_pending(
        self, client: TestClient, session: Session
    ) -> None:
        repository = PostgresVideoRepository(session)
        videos = [
            VideoFactory.build(source_url=f"https://youtu.be/{key}")
            for key in ("jNQXAC9IVRw", "dQw4w9WgXcQ", "9bZkp7q19f0")
        ]
        for video in videos:
            repository.add(video)
        for video in videos[:2]:
            video.start_download()
            video.mark_failed("Video unavailable")
            repository.save(video)
        session.commit()

        response = client.post("/videos/retry-failed")

        assert response.status_code == 202
        session.expire_all()
        for video in videos:
            row = session.get_one(VideoORM, video.id)
            assert (row.status, row.error) == (VideoStatus.PENDING, None)

    def test_skips_a_video_retried_or_removed_meanwhile(
        self,
        client: TestClient,
        session: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        repository = PostgresVideoRepository(session)
        retried = VideoFactory.build(source_url="https://youtu.be/jNQXAC9IVRw")
        failed = VideoFactory.build(source_url="https://youtu.be/dQw4w9WgXcQ")
        for video in (retried, failed):
            repository.add(video)
        failed.start_download()
        failed.mark_failed("Video unavailable")
        repository.save(failed)
        session.commit()
        purged = uuid7()
        monkeypatch.setattr(
            PostgresVideoRepository, "failed", lambda _: [retried.id, purged, failed.id]
        )

        response = client.post("/videos/retry-failed")

        assert response.status_code == 202
        session.expire_all()
        assert session.get_one(VideoORM, failed.id).status is VideoStatus.PENDING

    def test_returns_202_when_nothing_failed(self, client: TestClient) -> None:
        response = client.post("/videos/retry-failed")

        assert response.status_code == 202


class TestRemoveVideo:
    def test_returns_204_and_marks_a_failed_video_removed(
        self, client: TestClient, session: Session
    ) -> None:
        repository = PostgresVideoRepository(session)
        video = VideoFactory.build()
        repository.add(video)
        video.start_download()
        video.mark_failed("Video unavailable")
        repository.save(video)
        session.commit()

        response = client.delete(f"/videos/{video.id}")

        assert response.status_code == 204
        session.expire_all()
        assert session.get_one(VideoORM, video.id).status is VideoStatus.REMOVED

    def test_removing_twice_returns_204(
        self, client: TestClient, session: Session
    ) -> None:
        video = VideoFactory.build()
        PostgresVideoRepository(session).add(video)
        session.commit()
        client.delete(f"/videos/{video.id}")

        response = client.delete(f"/videos/{video.id}")

        assert response.status_code == 204

    def test_an_unknown_video_returns_404(self, client: TestClient) -> None:
        video_id = uuid7()

        response = client.delete(f"/videos/{video_id}")

        assert response.status_code == 404
        assert response.json() == {"detail": f"Video {video_id} not found"}

    def test_a_downloading_video_returns_409(
        self, client: TestClient, session: Session
    ) -> None:
        repository = PostgresVideoRepository(session)
        video = VideoFactory.build()
        repository.add(video)
        video.start_download()
        repository.save(video)
        session.commit()

        response = client.delete(f"/videos/{video.id}")

        assert response.status_code == 409
        assert response.json() == {
            "detail": f"Video {video.id} is DOWNLOADING; only a PENDING, FAILED "
            "or READY video can be removed"
        }


class TestListQueue:
    def test_returns_the_videos_that_are_not_ready(
        self, client: TestClient, session: Session
    ) -> None:
        repository = PostgresVideoRepository(session)
        video = VideoFactory.build()
        repository.add(video)
        video.start_download()
        video.mark_failed("Video unavailable")
        repository.save(video)
        session.commit()

        response = client.get("/videos/queue")

        assert response.status_code == 200
        page = response.json()
        assert page["totals"] == {"pending": 0, "downloading": 0, "failed": 1}
        [item] = page["items"]
        assert item["id"] == str(video.id)
        assert item["status"] == "FAILED"
        assert item["source_url"] == "https://youtu.be/jNQXAC9IVRw"
        assert item["error"] == "Video unavailable"

    def test_returns_an_empty_page_when_nothing_is_queued(
        self, client: TestClient
    ) -> None:
        response = client.get("/videos/queue")

        assert response.status_code == 200
        assert response.json() == {
            "items": [],
            "totals": {"pending": 0, "downloading": 0, "failed": 0},
        }

    @pytest.mark.parametrize("limit", [0, 101])
    def test_rejects_a_limit_out_of_range(self, client: TestClient, limit: int) -> None:
        response = client.get("/videos/queue", params={"limit": limit})

        assert response.status_code == 422


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
