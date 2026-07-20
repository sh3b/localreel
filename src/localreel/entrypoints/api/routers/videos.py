from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status

from localreel.containers import Container
from localreel.domain.commands import SubmitURL
from localreel.domain.unit_of_work import AbstractUnitOfWork
from localreel.entrypoints.api.schemas.videos import SubmitURLRequest
from localreel.service_layer.message_bus import MessageBus

router = APIRouter()


@router.post("/videos", status_code=status.HTTP_202_ACCEPTED)
@inject
def submit_url(
    body: SubmitURLRequest,
    uow: Annotated[AbstractUnitOfWork, Depends(Provide[Container.uow])],
    bus: Annotated[MessageBus, Depends(Provide[Container.message_bus])],
) -> None:
    with uow:
        bus.handle(SubmitURL(url=body.url))
