from typing import Annotated
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, status

from localreel.containers import Container
from localreel.domain.commands import RetryVideo, SubmitURL
from localreel.domain.unit_of_work import AbstractUnitOfWork
from localreel.entrypoints.api.schemas.videos import SubmitURLRequest
from localreel.service_layer.message_bus import MessageBus
from localreel.views.dtos import QueuePage, VideoPage, VideoSort
from localreel.views.videos import VideoView

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


@router.post("/videos/{video_id}/retry", status_code=status.HTTP_202_ACCEPTED)
@inject
def retry_video(
    video_id: UUID,
    uow: Annotated[AbstractUnitOfWork, Depends(Provide[Container.uow])],
    bus: Annotated[MessageBus, Depends(Provide[Container.message_bus])],
) -> None:
    with uow:
        bus.handle(RetryVideo(video_id=video_id))


@router.get("/videos")
@inject
def list_videos(
    view: Annotated[VideoView, Depends(Provide[Container.video_view])],
    sort: VideoSort = VideoSort.NEWEST,
    after: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 24,
) -> VideoPage:
    return view.list_videos(sort=sort, after=after, limit=limit)


@router.get("/videos/queue")
@inject
def list_queue(
    view: Annotated[VideoView, Depends(Provide[Container.video_view])],
    after: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 24,
) -> QueuePage:
    return view.list_queue(after=after, limit=limit)
