from contextlib import suppress
from typing import Annotated
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, status

from localreel.containers import Container
from localreel.domain.commands import RemoveVideo, RetryVideo, SubmitURL
from localreel.domain.exceptions import (
    DuplicateVideo,
    InvalidStatusTransition,
    UnsupportedSource,
    VideoNotFound,
)
from localreel.domain.unit_of_work import AbstractUnitOfWork
from localreel.domain.value_objects import SourceURL, VideoStatus
from localreel.entrypoints.api.schemas.videos import (
    SubmitOutcome,
    SubmitResult,
    SubmitURLRequest,
    SubmitURLsRequest,
)
from localreel.service_layer.message_bus import MessageBus
from localreel.views.dtos import QueuePage, SavedLink, VideoPage, VideoSort
from localreel.views.videos import VideoView

router = APIRouter()

OUTCOME_BY_STATUS: dict[VideoStatus, SubmitOutcome] = {
    VideoStatus.PENDING: "queued",
    VideoStatus.DOWNLOADING: "queued",
    VideoStatus.READY: "ready",
    VideoStatus.FAILED: "failed",
}


@router.post("/videos", status_code=status.HTTP_202_ACCEPTED)
@inject
def submit_url(
    body: SubmitURLRequest,
    uow: Annotated[AbstractUnitOfWork, Depends(Provide[Container.uow])],
    bus: Annotated[MessageBus, Depends(Provide[Container.message_bus])],
) -> None:
    source_url = SourceURL.parse(body.url)
    with uow:
        bus.handle(SubmitURL(source_url=source_url))


@router.post("/videos/batch")
@inject
def submit_urls(
    body: SubmitURLsRequest,
    uow: Annotated[AbstractUnitOfWork, Depends(Provide[Container.uow])],
    bus: Annotated[MessageBus, Depends(Provide[Container.message_bus])],
    view: Annotated[VideoView, Depends(Provide[Container.video_view])],
) -> list[SubmitResult]:
    # 1. Parse: split the links into supported and unsupported.
    sources: dict[str, SourceURL] = {}
    unsupported: dict[str, str] = {}
    for url in body.urls:
        try:
            sources[url] = SourceURL.parse(url)
        except UnsupportedSource as exc:
            unsupported[url] = str(exc)

    # 2. Save: one transaction per link, so one bad link never undoes the others.
    for source_url in sources.values():
        # A lost race means another request saved the link; the read reports it.
        with suppress(DuplicateVideo), uow:
            bus.handle(SubmitURL(source_url=source_url))

    # 3. Read what each saved link is now.
    saved: dict[str, SavedLink] = view.saved_links(
        [source_url.key for source_url in sources.values()]
    )

    # 4. Answer every link, in the order sent.
    results = []
    for url in body.urls:
        if url in unsupported:
            results.append(
                SubmitResult(url=url, result="unsupported", reason=unsupported[url])
            )
            continue
        link = saved[sources[url].key]
        results.append(
            SubmitResult(
                url=url,
                result=OUTCOME_BY_STATUS[link.status],
                video_id=link.id,
                reason=link.error,
            )
        )
    return results


@router.post("/videos/{video_id}/retry", status_code=status.HTTP_202_ACCEPTED)
@inject
def retry_video(
    video_id: UUID,
    uow: Annotated[AbstractUnitOfWork, Depends(Provide[Container.uow])],
    bus: Annotated[MessageBus, Depends(Provide[Container.message_bus])],
) -> None:
    with uow:
        bus.handle(RetryVideo(video_id=video_id))


# Not /videos/failed/retry: /videos/{video_id}/retry would take that path.
@router.post("/videos/retry-failed", status_code=status.HTTP_202_ACCEPTED)
@inject
def retry_failed_videos(
    uow: Annotated[AbstractUnitOfWork, Depends(Provide[Container.uow])],
    bus: Annotated[MessageBus, Depends(Provide[Container.message_bus])],
) -> None:
    with uow(commit=False):
        video_ids = uow.videos.failed()
    for video_id in video_ids:
        with suppress(InvalidStatusTransition, VideoNotFound), uow:
            bus.handle(RetryVideo(video_id=video_id))


@router.delete("/videos/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
def remove_video(
    video_id: UUID,
    uow: Annotated[AbstractUnitOfWork, Depends(Provide[Container.uow])],
    bus: Annotated[MessageBus, Depends(Provide[Container.message_bus])],
) -> None:
    with uow:
        bus.handle(RemoveVideo(video_id=video_id))


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
    limit: Annotated[int, Query(ge=1, le=100)] = 24,
) -> QueuePage:
    return view.list_queue(limit=limit)
