"""Session factory and transactional scope helper."""

import functools
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy.orm import Session, sessionmaker

from manga_recommender.db.engine import get_engine


@functools.lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Return the cached SQLAlchemy session factory."""
    return sessionmaker(bind=get_engine())


@contextmanager
def session_scope() -> Generator[Session]:
    """Yield a session, committing on success and rolling back on error.

    Always closes the session afterward.
    """
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session]:
    """Yield a request-scoped session and close it afterward.

    Does not commit. Read paths need no transaction, and a write path should
    commit explicitly.
    """
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
