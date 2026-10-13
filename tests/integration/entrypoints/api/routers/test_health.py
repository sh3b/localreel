from dependency_injector import providers
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from localreel.containers import Container


def _unreachable_db() -> None:
    raise OperationalError("SELECT 1", {}, Exception("connection refused"))


class TestHealth:
    def test_returns_200_when_the_database_answers(self, client: TestClient) -> None:
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "db": "ok"}

    def test_returns_503_when_the_database_is_unreachable(
        self, client: TestClient, container: Container
    ) -> None:
        container.session_factory.override(providers.Object(_unreachable_db))

        response = client.get("/health")

        assert response.status_code == 503
        assert response.json() == {"status": "unavailable", "db": "down"}
