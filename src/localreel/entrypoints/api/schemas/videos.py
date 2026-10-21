from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from localreel.domain.types import VideoVisibility

# One link, trimmed; a blank line is not a link.
Link = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

# Enough for a long paste, small enough that one request cannot flood the queue.
MAX_LINKS_PER_BATCH = 100


class SubmitURLRequest(BaseModel):
    url: str
    user_id: UUID
    visibility: VideoVisibility = VideoVisibility.PRIVATE


class SubmitURLsRequest(BaseModel):
    urls: list[Link] = Field(min_length=1, max_length=MAX_LINKS_PER_BATCH)
    user_id: UUID
    visibility: VideoVisibility = VideoVisibility.PRIVATE


class SubmitResult(BaseModel):
    url: str
    result: Literal["added", "duplicate", "unsupported"]
    reason: str | None = None
