from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query, status

from localreel.containers import Container
from localreel.domain.abstractions.unit_of_work import AbstractUnitOfWork
from localreel.domain.commands import SubmitURL
from localreel.domain.exceptions import UnsupportedSource
from localreel.entrypoints.api.schemas.videos import SubmitURLRequest
from localreel.service_layer.message_bus import MessageBus
from localreel.service_layer.views.dtos import VideoPage, VideoSort
from localreel.service_layer.views.videos import VideoView

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


@router.get("/videos")
@inject
def list_videos(
    sort: VideoSort = VideoSort.NEWEST,
    after: UUID | None = None,
    limit: int = Query(default=24, ge=1, le=100),
    video_view: VideoView = Depends(Provide[Container.video_view]),
) -> VideoPage:
    return video_view.list_videos(sort=sort, after=after, limit=limit)
