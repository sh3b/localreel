import pytest
from pydantic import ValidationError

from localreel.settings import Settings


class TestTimingSettings:
    @pytest.mark.parametrize(
        "field",
        [
            "download_poll_interval_sec",
            "download_timeout_sec",
            "transcode_poll_interval_sec",
            "transcode_timeout_sec",
        ],
    )
    @pytest.mark.parametrize("value", ["0", "-1"])
    def test_rejects_zero_and_negative(
        self, monkeypatch: pytest.MonkeyPatch, field: str, value: str
    ) -> None:
        monkeypatch.setenv(field.upper(), value)

        with pytest.raises(ValidationError, match=field):
            Settings()  # type: ignore[call-arg]
