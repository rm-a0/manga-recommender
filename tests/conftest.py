from collections.abc import Generator

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from manga_recommender.db.engine import get_engine
from manga_recommender.db.models.sources import Source


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
    def _restart_savepoint(session: Session, transaction: object) -> None:
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
