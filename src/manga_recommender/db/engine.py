import functools

from sqlalchemy import Engine, create_engine

from manga_recommender.config import get_database_settings


@functools.lru_cache
def get_engine() -> Engine:
    return create_engine(get_database_settings().url, pool_pre_ping=True)
