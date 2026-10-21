from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query, status

from localreel.containers import Container
from localreel.domain.abstractions.unit_of_work import AbstractUnitOfWork
from localreel.domain.commands import RetryVideo, SubmitURL
from localreel.domain.events import VideoIngested
from localreel.domain.exceptions import (
    InvalidStatusTransition,
    UnsupportedSource,
    VideoNotFound,
)
from localreel.entrypoints.api.schemas.videos import (
    SubmitResult,
    SubmitURLRequest,
    SubmitURLsRequest,
)
from localreel.service_layer.message_bus import MessageBus
from localreel.views.dtos import QueueItem, VideoPage, VideoSort
from localreel.views.videos import VideoView

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


@router.post("/videos/batch")
@inject
def submit_urls(
    body: SubmitURLsRequest,
    bus: MessageBus = Depends(Provide[Container.message_bus]),
    uow: AbstractUnitOfWork = Depends(Provide[Container.uow]),
) -> list[SubmitResult]:
    # One transaction per link, so one bad link never undoes the others.
    results: list[SubmitResult] = []
    for url in body.urls:
        command = SubmitURL(url=url, user_id=body.user_id, visibility=body.visibility)
        try:
            with uow:
                events = bus.handle(command)
        except UnsupportedSource as exc:
            results.append(SubmitResult(url=url, result="unsupported", reason=str(exc)))
            continue
        added = any(isinstance(event, VideoIngested) for event in events)
        results.append(SubmitResult(url=url, result="added" if added else "duplicate"))
    return results


@router.get("/videos/queue")
@inject
def queue(
    video_view: VideoView = Depends(Provide[Container.video_view]),
) -> list[QueueItem]:
    return video_view.queue()


@router.post("/videos/{video_id}/retry", status_code=status.HTTP_202_ACCEPTED)
@inject
def retry(
    video_id: UUID,
    bus: MessageBus = Depends(Provide[Container.message_bus]),
    uow: AbstractUnitOfWork = Depends(Provide[Container.uow]),
) -> None:
    try:
        with uow:
            bus.handle(RetryVideo(video_id=video_id))
    except VideoNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except InvalidStatusTransition as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
