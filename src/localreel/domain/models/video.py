from typing import ClassVar
from uuid import UUID

from localreel.domain.events import (
    SourceFileRemoved,
    TagsUpdated,
    VideoDownloaded,
    VideoFailed,
    VideoIngested,
    VideoReady,
    WatchRecorded,
)
from localreel.domain.exceptions import InvalidStatusTransition
from localreel.domain.messages import Event
from localreel.domain.types import VideoSource, VideoStatus, VideoVisibility


class Video:
    VALID_TRANSITIONS: ClassVar[dict[VideoStatus, frozenset[VideoStatus]]] = {
        # DOWNLOADED directly from PENDING covers LOCAL uploads, where the
        # file is already on disk and there is no download step.
        VideoStatus.PENDING: frozenset(
            {VideoStatus.DOWNLOADING, VideoStatus.DOWNLOADED, VideoStatus.FAILED}
        ),
        VideoStatus.DOWNLOADING: frozenset(
            {VideoStatus.DOWNLOADED, VideoStatus.FAILED}
        ),
        VideoStatus.DOWNLOADED: frozenset(
            {VideoStatus.TRANSCODING, VideoStatus.FAILED}
        ),
        VideoStatus.TRANSCODING: frozenset({VideoStatus.READY, VideoStatus.FAILED}),
        VideoStatus.READY: frozenset(),
        VideoStatus.FAILED: frozenset({VideoStatus.PENDING}),  # retry
    }

    def __init__(
        self,
        *,
        id: UUID,
        uploaded_by: UUID,
        source: VideoSource,
        source_url: str | None,
        source_url_hash: str | None,
        file_hash: str | None,
        visibility: VideoVisibility,
        status: VideoStatus,
        title: str | None,
        description: str | None,
        tags: list[str],
        duration_sec: int | None,
        hls_path: str | None,
        thumbnail_path: str | None,
        original_path: str | None,
        phash: str | None,
        score: float,
        view_count: int,
        source_file_available: bool,
        error_message: str | None,
    ):
        self.id = id
        self.uploaded_by = uploaded_by
        self.source = source
        self.source_url = source_url
        self.source_url_hash = source_url_hash
        self.file_hash = file_hash
        self.visibility = visibility
        self.status = status
        self.title = title
        self.description = description
        self.tags = tags
        self.duration_sec = duration_sec
        self.hls_path = hls_path
        self.thumbnail_path = thumbnail_path
        self.original_path = original_path
        self.phash = phash
        self.score = score
        self.view_count = view_count
        self.source_file_available = source_file_available
        self.error_message = error_message

        self.events: list[Event] = []

    @classmethod
    def create(
        cls,
        *,
        id: UUID,
        uploaded_by: UUID,
        source: VideoSource,
        source_url: str | None = None,
        source_url_hash: str | None = None,
        file_hash: str | None = None,
        visibility: VideoVisibility = VideoVisibility.PRIVATE,
    ) -> Video:
        video = cls(
            id=id,
            uploaded_by=uploaded_by,
            source=source,
            source_url=source_url,
            source_url_hash=source_url_hash,
            file_hash=file_hash,
            visibility=visibility,
            status=VideoStatus.PENDING,
            title=None,
            description=None,
            tags=[],
            duration_sec=None,
            hls_path=None,
            thumbnail_path=None,
            original_path=None,
            phash=None,
            score=0.0,
            view_count=0,
            source_file_available=True,
            error_message=None,
        )
        video.events.append(VideoIngested(video_id=id))
        return video

    # --- state machine ---

    def _transition(self, new_status: VideoStatus) -> None:
        if new_status not in self.VALID_TRANSITIONS[self.status]:
            raise InvalidStatusTransition(
                f"Invalid transition {self.status} -> {new_status} for video {self.id}"
            )
        self.status = new_status

    def mark_downloading(self) -> None:
        self._transition(VideoStatus.DOWNLOADING)

    def mark_downloaded(self, original_path: str) -> None:
        self._transition(VideoStatus.DOWNLOADED)
        self.original_path = original_path
        self.events.append(VideoDownloaded(video_id=self.id))

    def mark_transcoding(self) -> None:
        self._transition(VideoStatus.TRANSCODING)

    def mark_ready(self, hls_path: str, thumbnail_path: str) -> None:
        self._transition(VideoStatus.READY)
        self.hls_path = hls_path
        self.thumbnail_path = thumbnail_path
        self.events.append(VideoReady(video_id=self.id))

    def mark_failed(self, reason: str) -> None:
        self._transition(VideoStatus.FAILED)
        self.error_message = reason
        self.events.append(VideoFailed(video_id=self.id, reason=reason))

    # --- behaviour ---

    def set_visibility(self, visibility: VideoVisibility) -> None:
        if visibility == self.visibility:
            return
        self.visibility = visibility

    def record_watch(self, user_id: UUID) -> None:
        self.view_count += 1
        self.events.append(
            WatchRecorded(video_id=self.id, user_id=user_id, tags=list(self.tags))
        )

    @staticmethod
    def _normalize_tags(tags: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for tag in tags:
            tag = tag.strip().lower()
            if tag and tag not in seen:
                seen.add(tag)
                result.append(tag)
        return result

    def update_tags(self, tags: list[str]) -> None:
        new_tags = self._normalize_tags(tags)
        added = [t for t in new_tags if t not in self.tags]
        removed = [t for t in self.tags if t not in new_tags]
        if not added and not removed:
            return
        self.tags = new_tags
        self.events.append(
            TagsUpdated(
                video_id=self.id,
                tags=list(self.tags),
                tags_added=added,
                tags_removed=removed,
            )
        )

    def remove_source_file(self) -> None:
        self.source_file_available = False
        self.events.append(SourceFileRemoved(video_id=self.id))

    def collect_events(self) -> list[Event]:
        # Empty the list on handover, or the next handler holding this same
        # object would deliver these events again.
        events = self.events
        self.events = []
        return events
