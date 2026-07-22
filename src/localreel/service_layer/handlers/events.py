import logging
from uuid import uuid7

from localreel.domain.abstractions.unit_of_work import AbstractUnitOfWork
from localreel.domain.entities.download_job import DownloadJob
from localreel.domain.events import VideoIngested

logger = logging.getLogger(__name__)


class OnVideoIngestedHandler:
    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self._uow = uow

    def __call__(self, event: VideoIngested) -> None:
        self._uow.download_jobs.add(DownloadJob(id=uuid7(), video_id=event.video_id))
