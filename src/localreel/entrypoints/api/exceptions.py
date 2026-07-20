from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse

from localreel.domain.exceptions import DomainError, DuplicateVideo, UnsupportedSource

STATUS_BY_EXCEPTION: dict[type[DomainError], int] = {
    UnsupportedSource: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def handle_domain_error(_request: Request, exc: Exception) -> JSONResponse:
    # isinstance, so a subclass of a mapped exception gets its parent's status.
    # The first match wins: list a mapped subclass before its parent.
    code = status.HTTP_400_BAD_REQUEST
    for exception_type, mapped_code in STATUS_BY_EXCEPTION.items():
        if isinstance(exc, exception_type):
            code = mapped_code
            break
    return JSONResponse(status_code=code, content={"detail": str(exc)})


def handle_duplicate_video(_request: Request, _exc: Exception) -> Response:
    return Response(status_code=status.HTTP_202_ACCEPTED)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, handle_domain_error)
    app.add_exception_handler(DuplicateVideo, handle_duplicate_video)
