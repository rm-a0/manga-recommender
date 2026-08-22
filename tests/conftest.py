import os

# Force tests onto the local Docker Postgres test database, unconditionally
# overriding whatever `.env`/the environment sets `DB_URL` to (Supabase, the
# local dev database, anything). This must run before any import below
# triggers `get_database_settings()`/`get_engine()`, both `lru_cache`d on
# first call.
os.environ["DB_URL"] = "postgresql://postgres:password@localhost:5433/mangarec_test"

import time
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import event
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from alembic import command
from manga_recommender.db.engine import get_engine
from manga_recommender.db.models.sources import Source

REPO_ROOT = Path(__file__).parent.parent


@pytest.fixture(scope="session", autouse=True)
def _migrate_test_db() -> None:
    """Wait for the local Postgres container and migrate the test database.

    Runs once per test session, before any test touches the database.
    """
    deadline = time.monotonic() + 30
    while True:
        try:
            get_engine().connect().close()
            break
        except OperationalError:
            if time.monotonic() > deadline:
                raise RuntimeError(
                    "Could not reach the local test database at "
                    f"{os.environ['DB_URL']!r}. Run `make db-up` first."
                ) from None
            time.sleep(0.5)

    command.upgrade(Config(str(REPO_ROOT / "alembic.ini")), "head")


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
