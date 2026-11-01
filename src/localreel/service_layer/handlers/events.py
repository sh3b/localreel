from localreel.domain.downloader import AbstractDownloader
from localreel.domain.events import VideoFailed, VideoRemoved


class DiscardFilesHandler:
    def __init__(self, downloader: AbstractDownloader) -> None:
        self._downloader = downloader

    def __call__(self, event: VideoFailed | VideoRemoved) -> None:
        self._downloader.discard(video_id=event.video_id)
