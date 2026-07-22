"""Imperative SQLAlchemy mapping for the domain model."""

from typing import Any

from sqlalchemy import (
    ARRAY,
    Boolean,
    Column,
    Enum,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    Uuid,
    event,
)
from sqlalchemy.orm import registry

from localreel.domain.entities.download_job import DownloadJob
from localreel.domain.models.video import Video
from localreel.domain.types import VideoSource, VideoStatus, VideoVisibility

metadata = MetaData()
mapper_registry = registry(metadata=metadata)

videos = Table(
    "videos",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("uploaded_by", Uuid, nullable=False),
    Column("source", Enum(VideoSource, name="video_source"), nullable=False),
    Column("source_url", Text, nullable=True),
    Column("source_url_hash", String(64), nullable=True, unique=True),
    Column("file_hash", String(64), nullable=True),
    Column(
        "visibility", Enum(VideoVisibility, name="video_visibility"), nullable=False
    ),
    Column("status", Enum(VideoStatus, name="video_status"), nullable=False),
    Column("title", Text, nullable=True),
    Column("description", Text, nullable=True),
    Column("tags", ARRAY(Text), nullable=False),
    Column("duration_sec", Integer, nullable=True),
    Column("hls_path", Text, nullable=True),
    Column("thumbnail_path", Text, nullable=True),
    Column("original_path", Text, nullable=True),
    Column("phash", String(64), nullable=True),
    Column("score", Float, nullable=False),
    Column("view_count", Integer, nullable=False),
    Column("source_file_available", Boolean, nullable=False),
    Column("error_message", Text, nullable=True),
)

download_jobs = Table(
    "download_jobs",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("video_id", Uuid, nullable=False, unique=True),
)

mapper_registry.map_imperatively(Video, videos)
mapper_registry.map_imperatively(DownloadJob, download_jobs)


@event.listens_for(Video, "load")
def _init_events_on_load(video: Video, _context: Any) -> None:
    video.events = []
