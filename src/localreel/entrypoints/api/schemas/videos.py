from uuid import UUID

from pydantic import BaseModel

from localreel.domain.types import VideoVisibility


class SubmitURLRequest(BaseModel):
    url: str
    user_id: UUID
    visibility: VideoVisibility = VideoVisibility.PRIVATE
