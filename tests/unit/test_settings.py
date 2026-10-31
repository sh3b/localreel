import pytest
from pydantic import ValidationError

from localreel.settings import Settings


@pytest.mark.parametrize("value", ["0", "-1"])
def test_rejects_a_poll_interval_that_is_not_positive(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("WORKER_POLL_INTERVAL_SEC", value)

    with pytest.raises(ValidationError, match="worker_poll_interval_sec"):
        Settings()
