from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from localreel.containers import Container
from localreel.entrypoints.api.main import create_app


@pytest.fixture
def client(container: Container) -> Iterator[TestClient]:
    """Wires the rolled-back `container` from the top-level conftest into the
    app, so requests and test assertions share one transaction."""
    app = create_app(container)
    with TestClient(app) as test_client:
        yield test_client
    container.unwire()
