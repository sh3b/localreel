import pytest

from localreel.domain.exceptions import UnsupportedSource
from localreel.domain.value_objects import SourceURL, VideoSource


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


class TestSourceURLKey:
    @pytest.mark.parametrize(
        "url",
        [
            "https://www.youtube.com/watch?v=jNQXAC9IVRw",
            "https://youtu.be/jNQXAC9IVRw",
            "https://youtu.be/jNQXAC9IVRw?si=abc123",
            "https://m.youtube.com/watch?v=jNQXAC9IVRw&t=42s",
            "https://music.youtube.com/watch?v=jNQXAC9IVRw",
            "https://www.youtube.com/shorts/jNQXAC9IVRw",
            "https://www.youtube.com/live/jNQXAC9IVRw",
            "https://www.youtube-nocookie.com/embed/jNQXAC9IVRw",
        ],
    )
    def test_youtube_forms_share_one_key(self, url: str) -> None:
        assert SourceURL.parse(url).key == "youtube:jNQXAC9IVRw"

    @pytest.mark.parametrize(
        "url",
        [
            "https://www.youtube.com/@jawed",
            "https://www.youtube.com/playlist?list=PL123",
            "https://www.youtube.com/watch",
            "https://www.youtube.com/watch?v=short",
            "https://youtu.be/",
        ],
    )
    def test_rejects_youtube_urls_that_are_not_one_video(self, url: str) -> None:
        with pytest.raises(UnsupportedSource):
            SourceURL.parse(url)

    @pytest.mark.parametrize(
        ("url", "key"),
        [
            (
                "http://www.TikTok.com/@user/video/123#top",
                "https://tiktok.com/@user/video/123",
            ),
            (
                "https://m.facebook.com/watch?v=123",
                "https://facebook.com/watch?v=123",
            ),
        ],
    )
    def test_other_sources_key_on_the_cleaned_url(self, url: str, key: str) -> None:
        assert SourceURL.parse(url).key == key

    def test_keeps_the_url_as_submitted(self) -> None:
        url = "https://youtu.be/jNQXAC9IVRw?si=abc123"

        assert SourceURL.parse(url).url == url
