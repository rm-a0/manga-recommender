"""FastAPI application factory and the ASGI app object."""

from fastapi import FastAPI

from manga_recommender.api.routes import probes
from manga_recommender.core.config import get_app_settings


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_app_settings()
    app = FastAPI(
        title=settings.title,
        debug=settings.debug,
        version=settings.version,
    )
    # Probes stay unversioned at the root: `railway.toml` points its healthcheck
    # at `/health`, and they should not move with an API version.
    app.include_router(probes.router)
    return app


app = create_app()
