from uuid import UUID

from sqlalchemy.orm import Session

from localreel.adapters.orm import VideoORM
from localreel.adapters.repository import PostgresVideoRepository
from localreel.domain.models.video import Video
from localreel.domain.value_objects import SourceMetadata, VideoSource, VideoStatus
from localreel.views.dtos import QueueTotals, SavedLink, VideoCard, VideoSort
from localreel.views.videos import VideoView
from tests.factories import SourceMetadataFactory, VideoFactory


class TestListVideos:
    def test_returns_a_card_for_a_ready_video(
        self, session: Session, video_view: VideoView
    ) -> None:
        video = self._ready(session, "https://youtu.be/jNQXAC9IVRw")

        [card] = self._cards(video_view)

        assert card.id == video.id
        assert card.title == "Me at the zoo"
        assert card.uploader == "jawed"
        assert card.uploader_url == "https://www.youtube.com/@jawed"
        assert card.duration_sec == 19
        assert (card.width, card.height) == (320, 240)
        assert card.source is VideoSource.YOUTUBE
        assert card.source_url == "https://youtu.be/jNQXAC9IVRw"
        assert card.saved_at == session.get_one(VideoORM, video.id).created_at
        assert card.playback_url == f"/media/{video.id}.webm"
        assert card.thumbnail_url == f"/media/{video.id}.webp"

    def test_leaves_out_videos_that_are_not_ready(
        self, session: Session, video_view: VideoView
    ) -> None:
        repository = PostgresVideoRepository(session)
        repository.add(VideoFactory.build(source_url="https://youtu.be/dQw4w9WgXcQ"))
        downloading = VideoFactory.build(source_url="https://youtu.be/9bZkp7q19f0")
        repository.add(downloading)
        downloading.start_download()
        repository.save(downloading)
        session.commit()

        assert self._cards(video_view) == []

    def test_lists_the_newest_first(
        self, session: Session, video_view: VideoView
    ) -> None:
        older = self._ready(session, "https://youtu.be/jNQXAC9IVRw")
        newer = self._ready(session, "https://youtu.be/dQw4w9WgXcQ")

        cards = self._cards(video_view)

        assert [card.id for card in cards] == [newer.id, older.id]

    def test_lists_the_oldest_first_when_asked(
        self, session: Session, video_view: VideoView
    ) -> None:
        older = self._ready(session, "https://youtu.be/jNQXAC9IVRw")
        newer = self._ready(session, "https://youtu.be/dQw4w9WgXcQ")

        cards = self._cards(video_view, sort=VideoSort.OLDEST)

        assert [card.id for card in cards] == [older.id, newer.id]

    def test_a_full_page_points_to_the_next_one(
        self, session: Session, video_view: VideoView
    ) -> None:
        self._ready(session, "https://youtu.be/jNQXAC9IVRw")
        middle = self._ready(session, "https://youtu.be/dQw4w9WgXcQ")
        newest = self._ready(session, "https://youtu.be/9bZkp7q19f0")

        page = video_view.list_videos(sort=VideoSort.NEWEST, after=None, limit=2)

        assert [card.id for card in page.items] == [newest.id, middle.id]
        assert page.next_cursor == middle.id

    def test_the_last_page_has_no_cursor_even_when_full(
        self, session: Session, video_view: VideoView
    ) -> None:
        self._ready(session, "https://youtu.be/jNQXAC9IVRw")
        self._ready(session, "https://youtu.be/dQw4w9WgXcQ")

        page = video_view.list_videos(sort=VideoSort.NEWEST, after=None, limit=2)

        assert len(page.items) == 2
        assert page.next_cursor is None

    def test_continues_after_the_cursor_newest_first(
        self, session: Session, video_view: VideoView
    ) -> None:
        oldest = self._ready(session, "https://youtu.be/jNQXAC9IVRw")
        middle = self._ready(session, "https://youtu.be/dQw4w9WgXcQ")
        self._ready(session, "https://youtu.be/9bZkp7q19f0")

        cards = self._cards(video_view, after=middle.id)

        assert [card.id for card in cards] == [oldest.id]

    def test_continues_after_the_cursor_oldest_first(
        self, session: Session, video_view: VideoView
    ) -> None:
        self._ready(session, "https://youtu.be/jNQXAC9IVRw")
        middle = self._ready(session, "https://youtu.be/dQw4w9WgXcQ")
        newest = self._ready(session, "https://youtu.be/9bZkp7q19f0")

        cards = self._cards(video_view, sort=VideoSort.OLDEST, after=middle.id)

        assert [card.id for card in cards] == [newest.id]

    def test_facebook_titles_come_from_the_description(
        self, session: Session, video_view: VideoView
    ) -> None:
        self._ready(
            session,
            "https://www.facebook.com/watch/?v=10153231379946729",
            metadata=SourceMetadataFactory.build(
                title="Video", description="A caption worth reading"
            ),
        )

        [card] = self._cards(video_view)

        assert card.title == "A caption worth reading"

    def test_falls_back_to_the_description_without_a_title(
        self, session: Session, video_view: VideoView
    ) -> None:
        self._ready(
            session,
            "https://youtu.be/jNQXAC9IVRw",
            metadata=SourceMetadataFactory.build(title=None, description="Only this"),
        )

        [card] = self._cards(video_view)

        assert card.title == "Only this"

    def test_has_no_thumbnail_url_without_a_thumbnail(
        self, session: Session, video_view: VideoView
    ) -> None:
        self._ready(session, "https://youtu.be/jNQXAC9IVRw", thumbnail=False)

        [card] = self._cards(video_view)

        assert card.thumbnail_url is None

    @staticmethod
    def _cards(
        video_view: VideoView,
        sort: VideoSort = VideoSort.NEWEST,
        after: UUID | None = None,
    ) -> list[VideoCard]:
        return video_view.list_videos(sort=sort, after=after, limit=24).items

    @staticmethod
    def _ready(
        session: Session,
        source_url: str,
        metadata: SourceMetadata | None = None,
        thumbnail: bool = True,
    ) -> Video:
        repository = PostgresVideoRepository(session)
        video = VideoFactory.build(source_url=source_url)
        repository.add(video)
        video.start_download()
        video.mark_ready(
            file_path=f"{video.id}.webm",
            thumbnail_path=f"{video.id}.webp" if thumbnail else None,
            metadata=metadata or SourceMetadataFactory.build(),
        )
        repository.save(video)
        session.commit()
        return video


class TestListQueue:
    def test_lists_downloading_then_failed_then_waiting_and_counts_them(
        self, session: Session, video_view: VideoView
    ) -> None:
        repository = PostgresVideoRepository(session)
        pending = VideoFactory.build(source_url="https://youtu.be/jNQXAC9IVRw")
        downloading = VideoFactory.build(source_url="https://youtu.be/dQw4w9WgXcQ")
        failed = VideoFactory.build(source_url="https://youtu.be/9bZkp7q19f0")
        ready = VideoFactory.build(source_url="https://youtu.be/kJQP7kiw5Fk")
        for video in (pending, downloading, failed, ready):
            repository.add(video)
        for video in (downloading, failed, ready):
            video.start_download()
        failed.mark_failed("Video unavailable")
        ready.mark_ready(
            file_path="a.webm",
            thumbnail_path=None,
            metadata=SourceMetadataFactory.build(),
        )
        for video in (downloading, failed, ready):
            repository.save(video)
        session.commit()

        page = video_view.list_queue(limit=24)

        items = page.items
        assert [(item.id, item.status) for item in items] == [
            (downloading.id, VideoStatus.DOWNLOADING),
            (failed.id, VideoStatus.FAILED),
            (pending.id, VideoStatus.PENDING),
        ]
        assert items[1].source_url == "https://youtu.be/9bZkp7q19f0"
        assert items[1].error == "Video unavailable"
        assert items[1].saved_at == session.get_one(VideoORM, failed.id).created_at
        assert items[0].error is None
        assert page.totals == QueueTotals(pending=1, downloading=1, failed=1)

    def test_leaves_out_removed_videos(
        self, session: Session, video_view: VideoView
    ) -> None:
        kept = self._pending(session, "https://youtu.be/jNQXAC9IVRw")
        removed = self._pending(session, "https://youtu.be/dQw4w9WgXcQ")
        repository = PostgresVideoRepository(session)
        video = repository.get(removed.id, lock=False)
        video.remove()
        repository.save(video)
        session.commit()

        page = video_view.list_queue(limit=24)

        assert [item.id for item in page.items] == [kept.id]
        assert page.totals == QueueTotals(pending=1, downloading=0, failed=0)

    def test_lists_waiting_videos_newest_first(
        self, session: Session, video_view: VideoView
    ) -> None:
        older = self._pending(session, "https://youtu.be/jNQXAC9IVRw")
        newer = self._pending(session, "https://youtu.be/dQw4w9WgXcQ")

        items = video_view.list_queue(limit=24).items

        assert [item.id for item in items] == [newer.id, older.id]

    def test_the_limit_cuts_off_waiting_videos_not_a_failed_one(
        self, session: Session, video_view: VideoView
    ) -> None:
        failed = self._failed(session, "https://youtu.be/jNQXAC9IVRw")
        self._pending(session, "https://youtu.be/dQw4w9WgXcQ")
        newest = self._pending(session, "https://youtu.be/9bZkp7q19f0")

        page = video_view.list_queue(limit=2)

        assert [item.id for item in page.items] == [failed.id, newest.id]
        assert page.totals == QueueTotals(pending=2, downloading=0, failed=1)

    @staticmethod
    def _pending(session: Session, source_url: str) -> Video:
        video = VideoFactory.build(source_url=source_url)
        PostgresVideoRepository(session).add(video)
        session.commit()
        return video

    @staticmethod
    def _failed(session: Session, source_url: str) -> Video:
        repository = PostgresVideoRepository(session)
        video = VideoFactory.build(source_url=source_url)
        repository.add(video)
        video.start_download()
        video.mark_failed("Video unavailable")
        repository.save(video)
        session.commit()
        return video


class TestSavedLinks:
    def test_returns_the_saved_videos_by_source_key(
        self, session: Session, video_view: VideoView
    ) -> None:
        repository = PostgresVideoRepository(session)
        video = VideoFactory.build(source_url="https://youtu.be/jNQXAC9IVRw")
        repository.add(video)
        video.start_download()
        video.mark_failed("Video unavailable")
        repository.save(video)
        session.commit()

        saved = video_view.saved_links(["youtube:jNQXAC9IVRw", "youtube:dQw4w9WgXcQ"])

        assert saved == {
            "youtube:jNQXAC9IVRw": SavedLink(
                id=video.id, status=VideoStatus.FAILED, error="Video unavailable"
            )
        }

    def test_leaves_out_a_removed_video(
        self, session: Session, video_view: VideoView
    ) -> None:
        repository = PostgresVideoRepository(session)
        removed = VideoFactory.build(source_url="https://youtu.be/jNQXAC9IVRw")
        repository.add(removed)
        removed.remove()
        repository.save(removed)
        session.commit()

        assert video_view.saved_links(["youtube:jNQXAC9IVRw"]) == {}

    def test_skips_a_removed_video_and_finds_the_link_added_again(
        self, session: Session, video_view: VideoView
    ) -> None:
        repository = PostgresVideoRepository(session)
        removed = VideoFactory.build(source_url="https://youtu.be/jNQXAC9IVRw")
        repository.add(removed)
        removed.remove()
        repository.save(removed)
        again = VideoFactory.build(source_url="https://youtu.be/jNQXAC9IVRw")
        repository.add(again)
        session.commit()

        saved = video_view.saved_links(["youtube:jNQXAC9IVRw"])

        assert saved == {
            "youtube:jNQXAC9IVRw": SavedLink(
                id=again.id, status=VideoStatus.PENDING, error=None
            )
        }
