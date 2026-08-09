from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from localreel.domain.exceptions import (
    DomainError,
    InvalidStatusTransition,
    UnsupportedSource,
    VideoNotFound,
)

STATUS_BY_EXCEPTION: dict[type[Exception], int] = {
    UnsupportedSource: status.HTTP_422_UNPROCESSABLE_CONTENT,
    VideoNotFound: status.HTTP_404_NOT_FOUND,
    InvalidStatusTransition: status.HTTP_409_CONFLICT,
}


def handle_domain_error(_request: Request, exc: Exception) -> JSONResponse:
    code = STATUS_BY_EXCEPTION.get(type(exc), status.HTTP_400_BAD_REQUEST)
    return JSONResponse(status_code=code, content={"detail": str(exc)})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, handle_domain_error)
