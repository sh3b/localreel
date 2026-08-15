import pytest

from localreel.containers import Container
from localreel.views.videos import VideoView


@pytest.fixture
def video_view(container: Container) -> VideoView:
    return container.video_view()
