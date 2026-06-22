from fastapi import FastAPI

from streamdaq.api.routes import router


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

    return app


app = create_app()
