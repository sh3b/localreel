from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid7

from localreel.views.videos import VideoView


def _row(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": uuid7(),
        "source": "YOUTUBE",
        "title": "Fresh pasta in ninety seconds",
        "uploader": "Home Kitchen Notes",
        "tags": ["cooking"],
        "duration_sec": 92,
        "width": 1080,
        "height": 1920,
        "source_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "source_view_count": 1200,
        "playback_path": "abc/abc.mp4",
        "thumbnail_path": "abc/abc-thumbnail.jpg",
    }
    return row | overrides


class TestToCard:
    def test_media_paths_become_urls_under_media(self) -> None:
        card = VideoView.to_card(_row())

        assert card.playback_url == "/media/abc/abc.mp4"
        assert card.thumbnail_url == "/media/abc/abc-thumbnail.jpg"

    def test_missing_media_paths_give_no_urls(self) -> None:
        card = VideoView.to_card(_row(playback_path=None, thumbnail_path=None))

        assert card.playback_url is None
        assert card.thumbnail_url is None

    def test_saved_at_is_the_creation_time_in_the_uuid7_id(self) -> None:
        created_ms = 1_800_000_000_000  # 2027-01-15 08:00:00 UTC
        video_id = UUID(int=(created_ms << 80) | (0x7 << 76) | (0b10 << 62))

        card = VideoView.to_card(_row(id=video_id))

        assert card.saved_at == datetime(2027, 1, 15, 8, 0, tzinfo=UTC)
