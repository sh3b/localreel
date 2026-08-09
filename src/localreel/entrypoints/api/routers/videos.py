from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status

from localreel.containers import Container
from localreel.domain.abstractions.unit_of_work import AbstractUnitOfWork
from localreel.domain.commands import SubmitURL
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
        bus.handle(command)
