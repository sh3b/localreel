import json

import pytest
from starlette.requests import Request

from localreel.domain.exceptions import (
    DomainError,
    InvalidStatusTransition,
    UnsupportedSource,
    VideoNotFound,
)
from localreel.entrypoints.api.exceptions import handle_domain_error

REQUEST = Request({"type": "http"})


class DeletedVideo(VideoNotFound):
    pass


@pytest.mark.parametrize(
    ("exc", "status_code"),
    [
        (UnsupportedSource("ftp://x"), 422),
        (VideoNotFound("gone"), 404),
        (InvalidStatusTransition("READY -> PENDING"), 409),
        (DeletedVideo("gone"), 404),
        (DomainError("something else"), 400),
    ],
)
def test_maps_domain_errors_to_status_codes(exc, status_code):
    response = handle_domain_error(REQUEST, exc)

    assert response.status_code == status_code
    assert json.loads(bytes(response.body)) == {"detail": str(exc)}
