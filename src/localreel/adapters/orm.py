from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    Index,
    Integer,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from localreel.domain.value_objects import VideoSource, VideoStatus


class Base(DeclarativeBase):
    pass


# Enums are VARCHAR(32), not native Postgres enums: autogenerate misses values
# added to a native enum, and these enums grow one value at a time. The fixed
# length keeps a longer new value from needing a migration.
class VideoORM(Base):
    __tablename__ = "videos"
    # One live video per link. A REMOVED one waiting for the worker's cleanup
    # must not block the same link from being added again.
    __table_args__ = (
        Index(
            "uq_videos_source_key",
            "source_key",
            unique=True,
            postgresql_where=text("status <> 'REMOVED'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    source: Mapped[VideoSource] = mapped_column(
        Enum(VideoSource, name="video_source", native_enum=False, length=32)
    )
    source_url: Mapped[str] = mapped_column(Text)
    source_key: Mapped[str] = mapped_column(Text)
    status: Mapped[VideoStatus] = mapped_column(
        Enum(VideoStatus, name="video_status", native_enum=False, length=32)
    )
    attempts: Mapped[int] = mapped_column(Integer, server_default="0")
    file_path: Mapped[str | None] = mapped_column(Text)
    thumbnail_path: Mapped[str | None] = mapped_column(Text)
    source_title: Mapped[str | None] = mapped_column(Text)
    source_description: Mapped[str | None] = mapped_column(Text)
    source_uploader: Mapped[str | None] = mapped_column(Text)
    source_view_count: Mapped[int | None] = mapped_column(BigInteger)
    source_duration_sec: Mapped[int | None] = mapped_column(Integer)
    source_width: Mapped[int | None] = mapped_column(Integer)
    source_height: Mapped[int | None] = mapped_column(Integer)
    source_raw: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    modified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
