from uuid import UUID

from sqlalchemy import Enum, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from localreel.domain.value_objects import VideoSource, VideoStatus


class Base(DeclarativeBase):
    pass


# Enums are VARCHAR(32), not native Postgres enums: autogenerate misses values
# added to a native enum, and these enums grow one value at a time. The fixed
# length keeps a longer new value from needing a migration.
class VideoORM(Base):
    __tablename__ = "videos"
    __table_args__ = (UniqueConstraint("source_key", name="uq_videos_source_key"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    source: Mapped[VideoSource] = mapped_column(
        Enum(VideoSource, name="video_source", native_enum=False, length=32)
    )
    source_url: Mapped[str] = mapped_column(Text)
    source_key: Mapped[str] = mapped_column(Text)
    status: Mapped[VideoStatus] = mapped_column(
        Enum(VideoStatus, name="video_status", native_enum=False, length=32)
    )
