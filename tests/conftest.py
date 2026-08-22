import os
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import event
from sqlalchemy.orm import Session
from testcontainers.community.postgres import PostgresContainer

from alembic import command
from manga_recommender.db.engine import get_engine
from manga_recommender.db.models.sources import Source

REPO_ROOT = Path(__file__).parent.parent


@pytest.fixture(scope="session", autouse=True)
def _test_database() -> Generator[None, None, None]:
    """Spin up an ephemeral Postgres container and migrate it to head.

    Runs once per test session, before any test touches the database.
    Sets `DB_URL` to the container's URL - unconditionally overriding
    whatever `.env`/the environment sets it to (Supabase, the local dev
    database, anything) - before any other fixture's first call to the
    `lru_cache`d `get_database_settings()`/`get_engine()`. Requires Docker to
    be running locally.
    """
    with PostgresContainer("postgres:16") as postgres:
        os.environ["DB_URL"] = postgres.get_connection_url()
        command.upgrade(Config(str(REPO_ROOT / "alembic.ini")), "head")
        yield


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Yield a session whose writes never survive the test.

    Binds the session to a connection wrapped in an outer transaction, and
    restarts a SAVEPOINT after every inner commit. This isolates tests even
    from code under test that calls `session.commit()` itself.
    """
    connection = get_engine().connect()
    outer_transaction = connection.begin()
    session = Session(bind=connection)

    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(_session: Session, _transaction: object) -> None:
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


@pytest.fixture
def test_source(db_session: Session) -> Source:
    """Return a flushed, unsaved-past-the-test `Source` row."""
    source = Source(name="test_source")
    db_session.add(source)
    db_session.flush()
    return source
