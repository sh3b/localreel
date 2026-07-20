import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from localreel.adapters import orm
from localreel.containers import Container
from tests.factories.video import VideoFactory

URL_HASH = "c" * 64


class TestPostgresUnitOfWork:
    def test_exception_rolls_back_pending_writes(
        self, container: Container, session: Session
    ) -> None:
        uow = container.uow()

        with pytest.raises(RuntimeError):
            with uow:
                uow.videos.add(VideoFactory(source_url_hash=URL_HASH))
                assert uow.videos.get_by_source_url_hash(URL_HASH) is not None
                raise RuntimeError("boom")

        count = session.scalar(select(func.count()).select_from(orm.videos))
        assert count == 0
