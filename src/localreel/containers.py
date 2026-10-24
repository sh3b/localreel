from dependency_injector import containers, providers
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from localreel.adapters.downloader import YtDlpDownloader
from localreel.adapters.transcoder import FfmpegTranscoder
from localreel.adapters.unit_of_work import PostgresUnitOfWork
from localreel.domain.commands import (
    MarkDownloaded,
    MarkFailed,
    MarkReady,
    RecordHeartbeat,
    RetryVideo,
    SubmitURL,
)
from localreel.domain.events import (
    SourceFileRemoved,
    TagsUpdated,
    VideoDownloaded,
    VideoFailed,
    VideoIngested,
    VideoReady,
    WatchRecorded,
)
from localreel.domain.types import VideoStatus
from localreel.service_layer.download import download_next_pending
from localreel.service_layer.handlers.commands import (
    MarkDownloadedHandler,
    MarkFailedHandler,
    MarkReadyHandler,
    RecordHeartbeatHandler,
    RetryVideoHandler,
    SubmitURLHandler,
)
from localreel.service_layer.heartbeat import fail_stalled
from localreel.service_layer.message_bus import MessageBus
from localreel.service_layer.transcode import transcode_next_downloaded
from localreel.settings import Settings
from localreel.views.videos import VideoView


class Container(containers.DeclarativeContainer):
    settings = providers.Singleton(Settings)
    engine = providers.Singleton(
        create_engine,
        settings.provided.db_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3, "tcp_user_timeout": 5000},
    )
    session_factory: providers.Singleton[sessionmaker[Session]] = providers.Singleton(
        sessionmaker, bind=engine, autoflush=True
    )
    uow = providers.Singleton(PostgresUnitOfWork, session_factory=session_factory)

    downloader = providers.Singleton(
        YtDlpDownloader, downloads_dir=settings.provided.downloads_dir
    )

    transcoder = providers.Singleton(
        FfmpegTranscoder,
        media_dir=settings.provided.media_dir,
        timeout_sec=settings.provided.transcode_timeout_sec,
    )

    message_bus: providers.Singleton[MessageBus] = providers.Singleton(
        MessageBus,
        command_handlers=providers.Dict(
            {
                SubmitURL: providers.Singleton(SubmitURLHandler, uow),
                MarkDownloaded: providers.Singleton(MarkDownloadedHandler, uow),
                MarkReady: providers.Singleton(MarkReadyHandler, uow),
                MarkFailed: providers.Singleton(MarkFailedHandler, uow),
                RetryVideo: providers.Singleton(RetryVideoHandler, uow),
                RecordHeartbeat: providers.Singleton(RecordHeartbeatHandler, uow),
            }
        ),
        event_handlers=providers.Dict(
            {
                VideoIngested: providers.List(),
                VideoDownloaded: providers.List(),
                VideoReady: providers.List(),
                VideoFailed: providers.List(),
                WatchRecorded: providers.List(),
                TagsUpdated: providers.List(),
                SourceFileRemoved: providers.List(),
            }
        ),
    )

    # worker loop calls it repeatedly.
    download_pending = providers.Callable(
        download_next_pending,
        uow=uow,
        message_bus=message_bus,
        downloader=downloader,
        heartbeat_interval_sec=settings.provided.heartbeat_interval_sec,
    )

    transcode_pending = providers.Callable(
        transcode_next_downloaded,
        uow=uow,
        message_bus=message_bus,
        transcoder=transcoder,
        downloads_dir=settings.provided.downloads_dir,
        heartbeat_interval_sec=settings.provided.heartbeat_interval_sec,
    )

    fail_stalled_downloads = providers.Callable(
        fail_stalled,
        uow=uow,
        message_bus=message_bus,
        status=VideoStatus.DOWNLOADING,
        stalled_after_sec=settings.provided.stalled_after_sec,
    )

    fail_stalled_transcodes = providers.Callable(
        fail_stalled,
        uow=uow,
        message_bus=message_bus,
        status=VideoStatus.TRANSCODING,
        stalled_after_sec=settings.provided.stalled_after_sec,
    )

    video_view = providers.Singleton(VideoView, session_factory=session_factory)
