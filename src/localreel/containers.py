from dependency_injector import containers, providers
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from localreel.adapters.unit_of_work import PostgresUnitOfWork
from localreel.domain.commands import SubmitURL
from localreel.domain.events import VideoCreated
from localreel.service_layer.handlers.commands import SubmitURLHandler
from localreel.service_layer.handlers.events import AddVideoHandler
from localreel.service_layer.message_bus import MessageBus
from localreel.settings import Settings


class Container(containers.DeclarativeContainer):
    settings = providers.Singleton(Settings)
    engine = providers.Singleton(create_engine, settings.provided.db_url)
    session_factory: providers.Singleton[sessionmaker[Session]] = providers.Singleton(
        sessionmaker, bind=engine, autoflush=True
    )
    uow = providers.ContextLocalSingleton(
        PostgresUnitOfWork, session_factory=session_factory
    )

    message_bus = providers.Factory(
        MessageBus,
        command_handlers=providers.Dict(
            {SubmitURL: providers.Factory(SubmitURLHandler)}
        ),
        event_handlers=providers.Dict(
            {VideoCreated: providers.List(providers.Factory(AddVideoHandler, uow=uow))}
        ),
    )
