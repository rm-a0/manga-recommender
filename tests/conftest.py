import math
import os
import uuid
from collections.abc import Callable, Generator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import event
from sqlalchemy.orm import Session
from testcontainers.community.postgres import PostgresContainer

from alembic import command
from manga_recommender.db.engine import get_engine
from manga_recommender.db.models.manga import Manga
from manga_recommender.db.models.sources import Source
from manga_recommender.db.repositories.manga import (
    TagLinkValues,
    bulk_add_tags_to_manga,
    create_manga,
)
from manga_recommender.db.repositories.manga_embeddings import (
    EmbeddingValues,
    bulk_create_manga_embeddings,
)
from manga_recommender.db.repositories.tags import get_or_create_tag

REPO_ROOT = Path(__file__).parent.parent


@pytest.fixture(scope="session", autouse=True)
def _test_database() -> Generator[None]:
    """Spin up an ephemeral Postgres container and migrate it to head.

    Runs once per test session, before any test touches the database.
    Sets `DB_URL` to the container's URL - unconditionally overriding
    whatever `.env`/the environment sets it to (Supabase, the local dev
    database, anything) - before any other fixture's first call to the
    `lru_cache`d `get_database_settings()`/`get_engine()`. Requires Docker to
    be running locally.
    """
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        os.environ["DB_URL"] = postgres.get_connection_url()
        command.upgrade(Config(str(REPO_ROOT / "alembic.ini")), "head")
        yield


@pytest.fixture
def db_session() -> Generator[Session]:
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


DIMENSIONS = 384


def vector_at(degrees: float) -> list[float]:
    """Return a unit vector that sits `degrees` from the vector at zero.

    Only the first two dimensions carry a value, so the angle between two
    vectors is the difference of their degrees. The inner product of two unit
    vectors is the cosine of that angle.
    """
    radians = math.radians(degrees)
    vector = [0.0] * DIMENSIONS
    vector[0] = math.cos(radians)
    vector[1] = math.sin(radians)
    return vector


@pytest.fixture
def embedded_manga(db_session: Session) -> Callable[[str, float], Manga]:
    """Return a factory that creates one manga with a vector at an angle."""

    def _create(title: str, degrees: float) -> Manga:
        manga = create_manga(
            db_session,
            title=title,
            description=f"The description of {title}.",
        )
        db_session.flush()
        values: EmbeddingValues = {
            "manga_id": manga.id,
            "content_vector": vector_at(degrees),
            "model_name": "test-model",
            "computed_at": datetime.now(UTC),
        }
        bulk_create_manga_embeddings(db_session, [values])
        db_session.flush()
        return manga

    return _create


@pytest.fixture
def plain_manga(db_session: Session) -> Callable[[str], Manga]:
    """Return a factory that creates one manga without an embedding."""

    def _create(title: str) -> Manga:
        manga = create_manga(db_session, title=title, description=title)
        db_session.flush()
        return manga

    return _create


@pytest.fixture
def tag_manga(db_session: Session) -> Callable[[uuid.UUID, str], None]:
    """Return a function that attaches one tag to one manga."""

    def _tag(manga_id: uuid.UUID, name: str) -> None:
        tag = get_or_create_tag(db_session, name=name, category=None, is_explicit=False)
        db_session.flush()
        link: TagLinkValues = {
            "manga_id": manga_id,
            "tag_id": tag.id,
            "rank": None,
            "is_spoiler": False,
        }
        bulk_add_tags_to_manga(db_session, [link])
        db_session.flush()

    return _tag
