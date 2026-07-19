from dependency_injector import containers, providers
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from localreel.adapters.unit_of_work import PostgresUnitOfWork
from localreel.service_layer.message_bus import MessageBus
from localreel.settings import Settings


class Container(containers.DeclarativeContainer):
    settings = providers.Singleton(Settings)
    engine = providers.Singleton(create_engine, settings.provided.db_url)
    session_factory: providers.Singleton[sessionmaker[Session]] = providers.Singleton(
        sessionmaker, bind=engine, autoflush=True
    )
    uow = providers.Singleton(PostgresUnitOfWork, session_factory=session_factory)

    message_bus: providers.Singleton[MessageBus] = providers.Singleton(
        MessageBus,
        command_handlers=providers.Dict({}),
        event_handlers=providers.Dict({}),
    )
