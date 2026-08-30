"""SQLAlchemy engine construction and caching."""

import functools

from sqlalchemy import Engine, create_engine

from manga_recommender.core.config import get_database_settings


@functools.lru_cache
def get_engine() -> Engine:
    """Return the cached SQLAlchemy engine for the configured database URL."""
    args: dict[str, str] = {}
    settings = get_database_settings()
    if settings.statement_timeout is not None:
        args["options"] = f"-c statement_timeout={settings.statement_timeout}"

    return create_engine(
        settings.effective_url,
        pool_pre_ping=True,
        pool_size=settings.pool_size,
        max_overflow=settings.max_overflow,
        connect_args=args,
    )
