import hashlib
import logging
from uuid import uuid7

from localreel.domain.abstractions.unit_of_work import AbstractUnitOfWork
from localreel.domain.commands import SubmitURL
from localreel.domain.messages import Event
from localreel.domain.models.video import Video
from localreel.domain.types import VideoSource

logger = logging.getLogger(__name__)


class SubmitURLHandler:
    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self._uow = uow

    def __call__(self, cmd: SubmitURL) -> list[Event]:
        url_hash = self._sha256(cmd.url)
        if self._uow.videos.get_by_source_url_hash(url_hash) is not None:
            return []

        video = Video.create(
            id=uuid7(),
            uploaded_by=cmd.user_id,
            source=VideoSource.from_url(cmd.url),
            source_url=cmd.url,
            source_url_hash=url_hash,
            visibility=cmd.visibility,
        )
        self._uow.videos.add(video)
        return video.collect_events()

    @staticmethod
    def _sha256(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()
