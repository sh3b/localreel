from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from localreel.containers import Container
from localreel.entrypoints.api.main import create_app


@pytest.fixture
def client(container: Container) -> Iterator[TestClient]:
    """The app runs on the test's rolled-back container."""
    with TestClient(create_app(container)) as test_client:
        yield test_client
    container.unwire()
