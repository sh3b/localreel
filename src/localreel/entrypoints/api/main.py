from fastapi import FastAPI

from localreel.containers import Container
from localreel.entrypoints.api.routers import health, videos


def create_app(container: Container | None = None) -> FastAPI:
    container = container or Container()
    container.wire(modules=[videos])

    app = FastAPI(title="localreel")
    app.state.container = container
    app.include_router(health.router)
    app.include_router(videos.router)

    return app
