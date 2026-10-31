import json

from starlette.requests import Request

from localreel.domain.exceptions import DomainError, VideoNotFound
from localreel.entrypoints.api.exceptions import handle_domain_error


class VideoNotFoundSubclass(VideoNotFound):
    pass


def test_a_subclass_of_a_mapped_error_gets_its_parents_status() -> None:
    exc = VideoNotFoundSubclass("gone")

    response = handle_domain_error(Request({"type": "http"}), exc)

    assert response.status_code == 404
    assert json.loads(bytes(response.body)) == {"detail": "gone"}


def test_an_unmapped_error_is_a_400() -> None:
    exc = DomainError("something else")

    response = handle_domain_error(Request({"type": "http"}), exc)

    assert response.status_code == 400
    assert json.loads(bytes(response.body)) == {"detail": "something else"}
