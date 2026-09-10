from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from streamdaq.api.routes import router
from streamdaq.sessions import Session

# Global state to hold the StreamDAQ session
_ACTIVE_SESSION = None
_DEFAULT_GRACEFUL_KILL_TIMEOUT_SECONDS = 20


def set_active_session(session) -> None:
    global _ACTIVE_SESSION
    _ACTIVE_SESSION = session


def get_active_session() -> Session | None:
    return _ACTIVE_SESSION


def shut_down_active_session() -> None:
    session = get_active_session()
    if session:
        session.gracefully_kill(_DEFAULT_GRACEFUL_KILL_TIMEOUT_SECONDS)


def create_app() -> FastAPI:
    """
    Factory function to create the FastAPI application.
    """
    app = FastAPI(
        title="StreamDAQ API",
        description="Declarative control plane for the StreamDAQ engine.",
        version="1.0.0",
        on_shutdown=[shut_down_active_session],
    )

    app.include_router(router)

    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse(url="/docs")

    return app


app = create_app()
