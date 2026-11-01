import inspect
from typing import Any, get_args, get_type_hints

from localreel.adapters.repository import PostgresVideoRepository
from localreel.domain.models.video import Video


def mentions_video(hint: Any) -> bool:
    return hint is Video or any(mentions_video(arg) for arg in get_args(hint))


def test_only_add_get_save_and_delete_handle_videos() -> None:
    """add and get track the videos they take in or hand out, and the unit of
    work calls save or delete. Any other public method that takes or returns a Video
    would bypass tracking: return ids, and let the caller get the video."""
    handles_video = sorted(
        name
        for name, method in inspect.getmembers(
            PostgresVideoRepository, inspect.isfunction
        )
        if not name.startswith("_")
        and any(mentions_video(hint) for hint in get_type_hints(method).values())
    )

    assert handles_video == ["add", "delete", "get", "save"]
