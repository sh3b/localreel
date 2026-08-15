from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class SourceMetadata:
    """Provenance as the origin reported it, captured once at download."""

    source_id: str
    title: str | None
    description: str | None
    uploader: str | None
    uploader_id: str | None
    published_at: datetime | None
    view_count: int | None
    raw: dict[str, Any]
