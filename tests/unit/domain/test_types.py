import pytest

from localreel.domain.exceptions import UnsupportedSource
from localreel.domain.types import VideoSource


class TestVideoSourceFromUrl:
    @pytest.mark.parametrize(
        ("url", "source"),
        [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", VideoSource.YOUTUBE),
            ("https://youtu.be/dQw4w9WgXcQ", VideoSource.YOUTUBE),
            ("https://www.tiktok.com/@user/video/123", VideoSource.TIKTOK),
            ("https://www.facebook.com/watch?v=123", VideoSource.FACEBOOK),
            ("https://fb.watch/abc123/", VideoSource.FACEBOOK),
            ("HTTPS://YOUTU.BE/DQW4W9WGXCQ", VideoSource.YOUTUBE),
        ],
    )
    def test_detects_source(self, url: str, source: VideoSource) -> None:
        assert VideoSource.from_url(url) is source

    def test_unsupported_url_raises(self) -> None:
        with pytest.raises(UnsupportedSource):
            VideoSource.from_url("https://vimeo.com/12345")
