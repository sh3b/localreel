from dependency_injector import containers, providers
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from localreel.adapters.downloader import YtDlpDownloader
from localreel.adapters.transcoder import FfmpegTranscoder
from localreel.adapters.unit_of_work import PostgresUnitOfWork
from localreel.domain.commands import MarkDownloaded, MarkFailed, MarkReady, SubmitURL
from localreel.domain.events import (
    SourceFileRemoved,
    TagsUpdated,
    VideoDownloaded,
    VideoFailed,
    VideoIngested,
    VideoReady,
    WatchRecorded,
)
from localreel.service_layer.download import download_next_pending
from localreel.service_layer.handlers.commands import (
    MarkDownloadedHandler,
    MarkFailedHandler,
    MarkReadyHandler,
    SubmitURLHandler,
)
from localreel.service_layer.message_bus import MessageBus
from localreel.service_layer.transcode import transcode_next_downloaded
from localreel.settings import Settings


class Container(containers.DeclarativeContainer):
    settings = providers.Singleton(Settings)
    engine = providers.Singleton(create_engine, settings.provided.db_url)
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
    )

    transcode_pending = providers.Callable(
        transcode_next_downloaded,
        uow=uow,
        message_bus=message_bus,
        transcoder=transcoder,
    )
