from fastapi import FastAPI

from localreel.containers import Container
from localreel.entrypoints.api.exceptions import register_exception_handlers
from localreel.entrypoints.api.routers import videos


def create_app(container: Container | None = None) -> FastAPI:
    container = container or Container()
    container.wire(modules=[videos])

    app = FastAPI(title="localreel")
    app.include_router(videos.router)
    register_exception_handlers(app)
    return app
