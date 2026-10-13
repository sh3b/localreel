import logging

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from localreel.containers import Container
from localreel.entrypoints.api.schemas.health import HealthStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
@inject
def health(
    response: Response,
    session_factory: sessionmaker[Session] = Depends(
        Provide[Container.session_factory]
    ),
) -> HealthStatus:
    try:
        with session_factory() as session:
            session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("health check: database unreachable")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthStatus(status="unavailable", db="down")
    return HealthStatus(status="ok", db="ok")
