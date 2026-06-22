from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from streamdaq.api.routes import router

# Global state to hold the StreamDAQ session
_ACTIVE_SESSION = None

def set_active_session(session):
    global _ACTIVE_SESSION
    _ACTIVE_SESSION = session

def get_active_session():
    return _ACTIVE_SESSION

def create_app() -> FastAPI:
    """
    Factory function to create the FastAPI application.
    """
    app = FastAPI(
        title="StreamDAQ API",
        description="Declarative control plane for the StreamDAQ engine.",
        version="1.0.0",
    )

    app.include_router(router)

    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse(url="/docs")

    return app


app = create_app()
