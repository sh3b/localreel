from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, status

from localreel.containers import Container
from localreel.domain.abstractions.unit_of_work import AbstractUnitOfWork
from localreel.domain.commands import SubmitURL
from localreel.domain.exceptions import UnsupportedSource
from localreel.entrypoints.api.schemas.videos import SubmitURLRequest
from localreel.service_layer.message_bus import MessageBus

router = APIRouter()


@router.post("/videos", status_code=status.HTTP_202_ACCEPTED)
@inject
def submit_url(
    body: SubmitURLRequest,
    bus: MessageBus = Depends(Provide[Container.message_bus]),
    uow: AbstractUnitOfWork = Depends(Provide[Container.uow]),
) -> None:
    command = SubmitURL(url=body.url, user_id=body.user_id, visibility=body.visibility)
    with uow:
        try:
            bus.handle(command)
        except UnsupportedSource as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
            ) from exc
