from dependency_injector import containers, providers
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from localreel.adapters.unit_of_work import PostgresUnitOfWork
from localreel.settings import Settings


class Container(containers.DeclarativeContainer):
    settings = providers.Singleton(Settings)
    engine = providers.Singleton(create_engine, settings.provided.db_url)
    session_factory: providers.Singleton[sessionmaker[Session]] = providers.Singleton(
        sessionmaker, bind=engine, autoflush=True
    )
    uow = providers.Factory(PostgresUnitOfWork, session_factory=session_factory)
