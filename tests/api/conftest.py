from collections.abc import Generator, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from manga_recommender.api.main import create_app
from manga_recommender.db.session import get_db


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Yield a client whose requests share the rolled-back test session.

    Builds a fresh app per test, so one test's dependency overrides never
    leak into another.
    """
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def client_with_broken_db() -> Generator[TestClient, None, None]:
    """Yield a client whose database session raises on every query."""

    class _BrokenSession:
        def execute(self, *args: object, **kwargs: object) -> None:
            raise SQLAlchemyError("connection refused")

    def _broken_db() -> Iterator[_BrokenSession]:
        yield _BrokenSession()

    app = create_app()
    app.dependency_overrides[get_db] = _broken_db
    with TestClient(app) as test_client:
        yield test_client
