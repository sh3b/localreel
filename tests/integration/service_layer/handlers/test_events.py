import hashlib
from uuid import uuid7

from sqlalchemy import select
from sqlalchemy.orm import Session

from localreel.adapters import orm
from localreel.containers import Container
from localreel.domain.commands import SubmitURL
from localreel.domain.types import VideoVisibility


class TestVideoIngestedEnqueuesDownload:
    URL = "https://youtube.com/watch?v=dQw4w9WgXcQ"

    def test_submitting_a_url_enqueues_a_download_job(
        self, container: Container, session: Session
    ) -> None:
        uow = container.uow()

        with uow:
            container.message_bus().handle(
                SubmitURL(
                    url=self.URL,
                    user_id=uuid7(),
                    visibility=VideoVisibility.SHARED,
                )
            )

        url_hash = hashlib.sha256(self.URL.encode()).hexdigest()
        video = uow.videos.get_by_source_url_hash(url_hash)
        assert video is not None
        job_video_ids = session.scalars(select(orm.download_jobs.c.video_id)).all()
        assert list(job_video_ids) == [video.id]
