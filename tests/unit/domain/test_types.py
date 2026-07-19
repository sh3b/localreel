import pytest

from localreel.domain.exceptions import UnsupportedSource
from localreel.domain.types import VideoSource


class TestVideoSourceFromUrl:
    @pytest.mark.parametrize(
        ("url", "source"),
        [
            ("https://www.youtube.com/watch?v=jNQXAC9IVRw", VideoSource.YOUTUBE),
            ("https://youtube.com/watch?v=jNQXAC9IVRw", VideoSource.YOUTUBE),
            ("https://youtu.be/jNQXAC9IVRw", VideoSource.YOUTUBE),
            ("https://m.youtube.com/shorts/abc", VideoSource.YOUTUBE),
            ("https://WWW.YOUTUBE.COM/watch?v=x", VideoSource.YOUTUBE),
            ("HTTPS://YOUTU.BE/DQW4W9WGXCQ", VideoSource.YOUTUBE),
            ("http://www.youtube.com/watch?v=x", VideoSource.YOUTUBE),
            ("https://www.youtube.com:443/watch?v=x", VideoSource.YOUTUBE),
            ("https://www.youtube-nocookie.com/embed/x", VideoSource.YOUTUBE),
            ("https://www.tiktok.com/@user/video/123", VideoSource.TIKTOK),
            ("https://vm.tiktok.com/abc/", VideoSource.TIKTOK),
            ("https://www.facebook.com/reel/123", VideoSource.FACEBOOK),
            ("https://www.facebook.com/watch?v=123", VideoSource.FACEBOOK),
        ],
    )
    def test_detects_source(self, url: str, source: VideoSource) -> None:
        assert VideoSource.from_url(url) is source

    @pytest.mark.parametrize(
        "url",
        [
            "https://vimeo.com/12345",
            "http://169.254.169.254/latest/meta-data/?youtube.com",
            "http://db:5432/#youtu.be",
            "javascript:alert(1)//youtube.com",
            "https://notyoutube.com.evil.example/x.mp4",
            "https://notyoutube.com/watch?v=x",
            "https://youtube.com.evil.example/",
            "ftp://youtube.com/x",
            "https://youtube.com@evil.com/",
            "https://evil.com\\@youtube.com/",
            "https://youtube.com:8443/watch?v=x",
            "https://youtube.com:notaport/",
            "https://fb.watch/abc/",
            "youtube.com/watch?v=x",
            "",
        ],
    )
    def test_rejects_urls_not_on_a_supported_host(self, url: str) -> None:
        with pytest.raises(UnsupportedSource):
            VideoSource.from_url(url)
