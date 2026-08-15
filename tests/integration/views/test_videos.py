from datetime import UTC, datetime

from sqlalchemy.orm import Session

from localreel.adapters.repository import PostgresVideoRepository
from localreel.domain.models.video import Video
from localreel.domain.value_objects import SourceMetadata, VideoSource
from localreel.views.videos import VideoView
from tests.factories import SourceMetadataFactory, VideoFactory


class TestListVideos:
    def test_returns_a_card_for_a_ready_video(
        self, session: Session, video_view: VideoView
    ) -> None:
        video = self._ready(session, "https://youtu.be/jNQXAC9IVRw")

        [card] = video_view.list_videos()

        assert card.id == video.id
        assert card.title == "Me at the zoo"
        assert card.uploader == "jawed"
        assert card.duration_sec == 19
        assert card.source is VideoSource.YOUTUBE
        assert card.source_url == "https://youtu.be/jNQXAC9IVRw"
        assert card.saved_at == datetime.fromtimestamp(video.id.time / 1000, UTC)
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

        assert video_view.list_videos() == []

    def test_lists_the_newest_first(
        self, session: Session, video_view: VideoView
    ) -> None:
        older = self._ready(session, "https://youtu.be/jNQXAC9IVRw")
        newer = self._ready(session, "https://youtu.be/dQw4w9WgXcQ")

        cards = video_view.list_videos()

        assert [card.id for card in cards] == [newer.id, older.id]

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

        [card] = video_view.list_videos()

        assert card.title == "A caption worth reading"

    def test_falls_back_to_the_description_without_a_title(
        self, session: Session, video_view: VideoView
    ) -> None:
        self._ready(
            session,
            "https://youtu.be/jNQXAC9IVRw",
            metadata=SourceMetadataFactory.build(title=None, description="Only this"),
        )

        [card] = video_view.list_videos()

        assert card.title == "Only this"

    def test_has_no_thumbnail_url_without_a_thumbnail(
        self, session: Session, video_view: VideoView
    ) -> None:
        self._ready(session, "https://youtu.be/jNQXAC9IVRw", thumbnail=False)

        [card] = video_view.list_videos()

        assert card.thumbnail_url is None

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
