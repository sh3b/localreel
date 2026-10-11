import logging
import signal
import time
from types import FrameType

from localreel.containers import Container

logger = logging.getLogger(__name__)


def run(container: Container) -> None:
    poll_interval = container.settings().transcode_poll_interval_sec
    while True:
        did_work: bool = container.transcode_pending()
        if not did_work:
            time.sleep(poll_interval)


def _stop(signum: int, frame: FrameType | None) -> None:
    raise SystemExit(128 + signum)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    signal.signal(signal.SIGTERM, _stop)
    run(Container())


if __name__ == "__main__":
    main()
