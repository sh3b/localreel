from dependency_injector import containers, providers
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from localreel.adapters.downloader import YtDlpDownloader
from localreel.adapters.unit_of_work import PostgresUnitOfWork
from localreel.domain.commands import (
    MarkFailed,
    MarkReady,
    RemoveVideo,
    ResetDownload,
    RetryVideo,
    StartDownload,
    SubmitURL,
)
from localreel.domain.events import VideoFailed, VideoRemoved
from localreel.service_layer.download_service import DownloadService
from localreel.service_layer.handlers.commands import (
    MarkFailedHandler,
    MarkReadyHandler,
    RemoveVideoHandler,
    ResetDownloadHandler,
    RetryVideoHandler,
    StartDownloadHandler,
    SubmitURLHandler,
)
from localreel.service_layer.handlers.events import DiscardFilesHandler
from localreel.service_layer.message_bus import MessageBus
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
    uow = providers.ContextLocalSingleton(
        PostgresUnitOfWork, session_factory=session_factory
    )
    downloader = providers.Singleton(
        YtDlpDownloader, downloads_dir=settings.provided.downloads_dir
    )

    message_bus = providers.Factory(
        MessageBus,
        uow=uow,
        command_handlers=providers.Dict(
            {
                SubmitURL: providers.Factory(SubmitURLHandler, uow=uow),
                StartDownload: providers.Factory(StartDownloadHandler, uow=uow),
                ResetDownload: providers.Factory(ResetDownloadHandler, uow=uow),
                MarkReady: providers.Factory(MarkReadyHandler, uow=uow),
                MarkFailed: providers.Factory(MarkFailedHandler, uow=uow),
                RetryVideo: providers.Factory(RetryVideoHandler, uow=uow),
                RemoveVideo: providers.Factory(RemoveVideoHandler, uow=uow),
            }
        ),
        event_handlers=providers.Dict(
            {
                VideoFailed: providers.List(
                    providers.Factory(DiscardFilesHandler, downloader=downloader)
                ),
                VideoRemoved: providers.List(
                    providers.Factory(DiscardFilesHandler, downloader=downloader)
                ),
            }
        ),
    )
    download_service = providers.Factory(
        DownloadService, uow=uow, message_bus=message_bus, downloader=downloader
    )
    video_view = providers.Factory(VideoView, session_factory=session_factory)
