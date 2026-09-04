"""FastAPI application factory and the ASGI app object."""

from fastapi import FastAPI

from manga_recommender.api.routes import authors, manga, probes, tags
from manga_recommender.core.config import get_app_settings, get_logging_settings
from manga_recommender.core.logging_config import configure_logging


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app_settings = get_app_settings()
    log_settings = get_logging_settings()
    configure_logging(
        level=log_settings.level,
        debug=app_settings.debug,
    )
    app = FastAPI(
        title=app_settings.title,
        debug=app_settings.debug,
        version=app_settings.version,
    )
    app.include_router(probes.router)
    app.include_router(manga.router)
    app.include_router(authors.router)
    app.include_router(tags.router)
    return app


app = create_app()
