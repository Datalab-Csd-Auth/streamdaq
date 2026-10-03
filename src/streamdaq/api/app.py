from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from streamdaq.__about__ import __version__
from streamdaq.api.routes import router
from streamdaq.api.utils import DEFAULT_GRACEFUL_KILL_TIMEOUT_SECONDS

if TYPE_CHECKING:
    from streamdaq.sessions import Session


class StreamdaqApi:
    def __init__(self, session: "Session") -> None:
        self.session = session
        self.app = self._build_app()

    def _build_app(self) -> FastAPI:
        app = FastAPI(
            title="Streamdaq API",
            description="Control plane for the Streamdaq engine.",
            version=__version__,
            lifespan=self.lifespan,
        )
        app.state.session = self.session
        app.include_router(router)

        @app.get("/", include_in_schema=False)
        async def root():
            return RedirectResponse(url="/docs")

        return app

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):  # https://fastapi.tiangolo.com/advanced/events/
        yield
        self.session.gracefully_kill(DEFAULT_GRACEFUL_KILL_TIMEOUT_SECONDS)
