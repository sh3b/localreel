import logging
import time

from localreel.containers import Container

logger = logging.getLogger(__name__)


def run(container: Container) -> None:
    poll_interval = container.settings().transcode_poll_interval_sec
    while True:
        did_work: bool = container.transcode_pending()
        if not did_work:
            time.sleep(poll_interval)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    run(Container())


if __name__ == "__main__":
    main()
