from uuid import UUID

from yt_dlp import YoutubeDL

from localreel.domain.abstractions.downloader import AbstractDownloader


class YtDlpDownloader(AbstractDownloader):
    def __init__(self, downloads_dir: str) -> None:
        self._downloads_dir = downloads_dir

    def download(self, *, url: str, video_id: UUID) -> str:
        options = {
            "outtmpl": f"{self._downloads_dir}/{video_id}.%(ext)s",
            "quiet": True,
            "noprogress": True,
        }
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            # `requested_downloads[0].filepath` is the final path after any
            # merge/postprocessing, unlike prepare_filename() which predates it.
            return str(info["requested_downloads"][0]["filepath"])
