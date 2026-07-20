from uuid import uuid7

import pytest

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
from localreel.domain.models.video import Video
from localreel.domain.types import VideoSource, VideoStatus, VideoVisibility
from tests.factories.video import VideoFactory


class TestCreate:
    def test_initial_state(self):
        vid, uid = uuid7(), uuid7()
        video = Video.create(id=vid, uploaded_by=uid, source=VideoSource.YOUTUBE)

        assert video.id == vid
        assert video.uploaded_by == uid
        assert video.status is VideoStatus.PENDING
        assert video.visibility is VideoVisibility.PRIVATE
        assert video.tags == []
        assert video.view_count == 0
        assert video.source_file_available is False
        assert video.error_message is None

    def test_emits_video_ingested(self):
        vid = uuid7()
        video = Video.create(id=vid, uploaded_by=uuid7(), source=VideoSource.TIKTOK)

        assert video.events == [VideoIngested(video_id=vid)]


class TestStatusTransitions:
    def test_url_video_happy_path(self):
        video = VideoFactory()

        video.mark_downloading()
        assert video.status is VideoStatus.DOWNLOADING

        video.mark_downloaded("/media/orig/v.mp4")
        assert video.status is VideoStatus.DOWNLOADED  # type: ignore[comparison-overlap]
        assert video.original_path == "/media/orig/v.mp4"
        assert video.source_file_available is True

        video.mark_transcoding()
        assert video.status is VideoStatus.TRANSCODING

        video.mark_ready("/media/hls/v", "/media/thumbs/v.jpg")
        assert video.status is VideoStatus.READY
        assert video.hls_path == "/media/hls/v"
        assert video.thumbnail_path == "/media/thumbs/v.jpg"

    def test_local_upload_skips_downloading(self):
        video = VideoFactory(source=VideoSource.LOCAL)

        video.mark_downloaded("/media/orig/upload.mp4")

        assert video.status is VideoStatus.DOWNLOADED

    def test_happy_path_emits_events_in_order(self):
        video = VideoFactory()

        video.mark_downloading()
        video.mark_downloaded("/media/orig/v.mp4")
        video.mark_transcoding()
        video.mark_ready("/media/hls/v", "/media/thumbs/v.jpg")

        assert video.events == [
            VideoDownloaded(video_id=video.id),
            VideoReady(video_id=video.id),
        ]

    def test_can_fail_from_any_in_flight_status(self):
        for advance in [
            lambda v: None,
            lambda v: v.mark_downloading(),
            lambda v: (v.mark_downloading(), v.mark_downloaded("/p")),
            lambda v: (
                v.mark_downloading(),
                v.mark_downloaded("/p"),
                v.mark_transcoding(),
            ),
        ]:
            video = VideoFactory()
            advance(video)

            video.mark_failed("boom")

            assert video.status is VideoStatus.FAILED
            assert video.error_message == "boom"
            assert video.events[-1] == VideoFailed(video_id=video.id, reason="boom")

    def test_ready_is_terminal(self):
        video = VideoFactory()
        video.mark_downloading()
        video.mark_downloaded("/p")
        video.mark_transcoding()
        video.mark_ready("/hls", "/thumb")

        for illegal in [
            video.mark_downloading,
            video.mark_transcoding,
            lambda: video.mark_downloaded("/p"),
            lambda: video.mark_ready("/hls", "/thumb"),
            lambda: video.mark_failed("boom"),
        ]:
            with pytest.raises(InvalidStatusTransition):
                illegal()

    def test_cannot_skip_pipeline_steps(self):
        video = VideoFactory()

        with pytest.raises(InvalidStatusTransition):
            video.mark_transcoding()
        with pytest.raises(InvalidStatusTransition):
            video.mark_ready("/hls", "/thumb")

    def test_rejected_transition_leaves_video_untouched(self):
        video = VideoFactory()

        with pytest.raises(InvalidStatusTransition):
            video.mark_ready("/hls", "/thumb")

        assert video.status is VideoStatus.PENDING
        assert video.hls_path is None
        assert video.thumbnail_path is None
        assert video.events == []

    def test_transition_table_covers_every_status(self):
        assert set(Video.VALID_TRANSITIONS) == set(VideoStatus)

    def test_failed_can_be_retried_to_pending(self):
        assert VideoStatus.PENDING in Video.VALID_TRANSITIONS[VideoStatus.FAILED]


class TestUpdateTags:
    def test_sets_tags_and_emits_delta(self):
        video = VideoFactory()

        video.update_tags(["cats", "dogs"])

        assert video.tags == ["cats", "dogs"]
        assert video.events == [
            TagsUpdated(
                video_id=video.id,
                tags=["cats", "dogs"],
                tags_added=["cats", "dogs"],
                tags_removed=[],
            )
        ]

    def test_normalizes_strips_lowercases_and_dedupes(self):
        video = VideoFactory()

        video.update_tags(["  Cats ", "DOGS", "cats", "", "   "])

        assert video.tags == ["cats", "dogs"]

    def test_tracks_added_and_removed(self):
        video = VideoFactory()
        video.update_tags(["cats", "dogs"])
        video.events.clear()

        video.update_tags(["dogs", "birds"])

        event = video.events[0]
        assert isinstance(event, TagsUpdated)
        assert event.tags == ["dogs", "birds"]
        assert event.tags_added == ["birds"]
        assert event.tags_removed == ["cats"]

    def test_noop_update_emits_nothing(self):
        video = VideoFactory()
        video.update_tags(["cats", "dogs"])
        video.events.clear()

        video.update_tags(["CATS", " dogs "])

        assert video.events == []
        assert video.tags == ["cats", "dogs"]


class TestSetVisibility:
    def test_changes_visibility(self):
        video = VideoFactory()

        video.set_visibility(VideoVisibility.SHARED)

        assert video.visibility is VideoVisibility.SHARED

    def test_noop_when_unchanged(self):
        video = VideoFactory()

        video.set_visibility(VideoVisibility.PRIVATE)

        assert video.visibility is VideoVisibility.PRIVATE


class TestRecordWatch:
    def test_increments_view_count_and_emits_event(self):
        video = VideoFactory()
        video.update_tags(["cats"])
        video.events.clear()
        watcher = uuid7()

        video.record_watch(watcher)
        video.record_watch(watcher)

        assert video.view_count == 2
        assert video.events == [
            WatchRecorded(video_id=video.id, user_id=watcher, tags=["cats"]),
            WatchRecorded(video_id=video.id, user_id=watcher, tags=["cats"]),
        ]

    def test_event_tags_are_a_snapshot(self):
        video = VideoFactory()
        video.update_tags(["cats"])
        video.events.clear()

        video.record_watch(uuid7())
        video.update_tags(["dogs"])

        watch_event = video.events[0]
        assert isinstance(watch_event, WatchRecorded)
        assert watch_event.tags == ["cats"]


class TestRemoveSourceFile:
    def test_marks_unavailable_and_emits_event(self):
        video = VideoFactory()

        video.remove_source_file()

        assert video.source_file_available is False
        assert video.events == [SourceFileRemoved(video_id=video.id)]


class TestCollectEvents:
    def test_returns_the_events_and_empties_the_list(self):
        video = VideoFactory(clear_events=False)

        events = video.collect_events()

        assert events == [VideoIngested(video_id=video.id)]
        assert video.events == []
        assert video.collect_events() == []
