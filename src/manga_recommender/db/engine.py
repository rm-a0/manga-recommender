"""SQLAlchemy engine construction and caching."""

import functools

from sqlalchemy import Engine, create_engine

from manga_recommender.core.config import get_database_settings


@functools.lru_cache
def get_engine() -> Engine:
    """Return the cached SQLAlchemy engine for the configured database URL."""
    return create_engine(get_database_settings().url, pool_pre_ping=True)
