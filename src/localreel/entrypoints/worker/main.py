import logging
import time

from localreel.containers import Container
from localreel.service_layer.download_service import DownloadService


class Worker:
    def __init__(self, *, service: DownloadService, poll_interval_sec: float) -> None:
        self._service = service
        self._poll_interval_sec = poll_interval_sec

    def run(self) -> None:
        self._service.reset_interrupted_downloads()
        while True:
            if not self._service.download_next():
                time.sleep(self._poll_interval_sec)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    container = Container()
    Worker(
        service=container.download_service(),
        poll_interval_sec=container.settings().worker_poll_interval_sec,
    ).run()


if __name__ == "__main__":
    main()
