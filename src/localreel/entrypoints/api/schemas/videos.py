from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

# One link, trimmed; a blank line is not a link.
Link = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

# Enough for a long paste, small enough that one request cannot flood the queue.
MAX_LINKS_PER_BATCH = 100

# What a link is now: ready in the library, queued on its way, failed on an
# earlier try (reason has the error), or unsupported and not saved.
SubmitOutcome = Literal["ready", "queued", "failed", "unsupported"]


class SubmitURLRequest(BaseModel):
    url: str


class SubmitURLsRequest(BaseModel):
    urls: list[Link] = Field(min_length=1, max_length=MAX_LINKS_PER_BATCH)


class SubmitResult(BaseModel):
    url: str
    result: SubmitOutcome
    video_id: UUID | None = None
    reason: str | None = None
