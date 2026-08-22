import uuid
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from manga_recommender.db.models.sources import Source
from manga_recommender.db.repositories.genres import create_genre
from manga_recommender.db.repositories.manga import create_manga, get_manga_by_mal_id
from manga_recommender.db.repositories.manga_external_rating import (
    get_external_rating_by_manga_and_source,
)
from manga_recommender.ingestion import loader
from manga_recommender.ingestion.base import NormalizedMangaRecord
from manga_recommender.ingestion.loader import _sync_genres_for_manga, load_batch


@pytest.fixture
def patched_session_scope(
    monkeypatch: pytest.MonkeyPatch, db_session: Session
) -> Generator[Session, None, None]:
    """Point `loader.session_scope` at the rolled-back test session.

    `load_batch` opens its own `session_scope()` against the real engine,
    which would otherwise bypass the `db_session` fixture's rollback.
    """

    @contextmanager
    def _fake_scope() -> Iterator[Session]:
        yield db_session
        db_session.flush()

    monkeypatch.setattr(loader, "session_scope", _fake_scope)
    yield db_session


def _record(
    external_id: str,
    *,
    mal_id: int | None = None,
    title: str = "Test Manga",
    genres: list[str] | None = None,
    raw_score: float | None = None,
) -> NormalizedMangaRecord:
    return NormalizedMangaRecord(
        external_id=external_id,
        mal_id=mal_id,
        title=title,
        author="Test Author",
        status=None,
        description=None,
        genres=genres,
        published_date=None,
        raw_score=raw_score,
        raw_scale_max=10.0,
        votes_count=100,
        fetched_at=datetime.now(UTC),
    )


class TestSyncGenresForManga:
    def test_attaches_genres_and_populates_the_cache(self, db_session: Session) -> None:
        manga = create_manga(db_session, title="One Piece", author="Eiichiro Oda")
        genre_cache: dict[str, uuid.UUID] = {}

        _sync_genres_for_manga(
            db_session,
            genre_cache,
            {"action", "adventure"},
            {manga.id: ["action", "adventure"]},
        )

        db_session.expire_all()
        assert {genre.name for genre in manga.genres} == {"action", "adventure"}
        assert genre_cache.keys() == {"action", "adventure"}

    def test_reuses_cached_genre_ids_without_a_bulk_lookup(
        self, db_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        manga = create_manga(db_session, title="Berserk", author="Kentaro Miura")
        genre = create_genre(db_session, name="dark fantasy")
        genre_cache = {"dark fantasy": genre.id}

        def _fail_if_called(*_args: object, **_kwargs: object) -> None:
            raise AssertionError("bulk_get_or_create_genres should not be called")

        monkeypatch.setattr(loader, "bulk_get_or_create_genres", _fail_if_called)

        _sync_genres_for_manga(
            db_session,
            genre_cache,
            {"dark fantasy"},
            {manga.id: ["dark fantasy"]},
        )

        db_session.expire_all()
        assert [g.id for g in manga.genres] == [genre.id]

    def test_does_not_duplicate_existing_genres(self, db_session: Session) -> None:
        manga = create_manga(db_session, title="Vagabond", author="Takehiko Inoue")
        genre_cache: dict[str, uuid.UUID] = {}
        _sync_genres_for_manga(
            db_session, genre_cache, {"action"}, {manga.id: ["action"]}
        )

        _sync_genres_for_manga(
            db_session,
            genre_cache,
            {"action", "drama"},
            {manga.id: ["action", "drama"]},
        )

        db_session.expire_all()
        assert {genre.name for genre in manga.genres} == {"action", "drama"}


class TestLoadBatch:
    def test_creates_manga_genres_and_ratings(
        self, patched_session_scope: Session, test_source: Source
    ) -> None:
        records = [
            _record("1", mal_id=101, title="Chainsaw Man", genres=["Action", "Horror"]),
            _record("2", mal_id=None, title="No Mal Id Manga", genres=["Drama"]),
        ]

        load_batch(records, test_source.id, genre_cache={})

        manga_with_mal_id = get_manga_by_mal_id(patched_session_scope, 101)
        assert manga_with_mal_id is not None
        assert manga_with_mal_id.title == "Chainsaw Man"
        assert {g.name for g in manga_with_mal_id.genres} == {"action", "horror"}

        rating = get_external_rating_by_manga_and_source(
            patched_session_scope, manga_with_mal_id.id, test_source.id
        )
        assert rating is not None
        assert rating.votes_count == 100

    def test_upserts_existing_manga_by_mal_id(
        self, patched_session_scope: Session, test_source: Source
    ) -> None:
        load_batch(
            [_record("1", mal_id=202, title="Old Title")],
            test_source.id,
            genre_cache={},
        )

        load_batch(
            [_record("1", mal_id=202, title="New Title")],
            test_source.id,
            genre_cache={},
        )

        manga = get_manga_by_mal_id(patched_session_scope, 202)
        assert manga is not None
        assert manga.title == "New Title"

    def test_shares_the_genre_cache_across_calls(
        self, patched_session_scope: Session, test_source: Source
    ) -> None:
        genre_cache: dict[str, uuid.UUID] = {}
        load_batch(
            [_record("1", mal_id=303, genres=["Action"])],
            test_source.id,
            genre_cache,
        )
        cached_id = genre_cache["action"]

        load_batch(
            [_record("2", mal_id=304, genres=["Action"])],
            test_source.id,
            genre_cache,
        )

        assert genre_cache["action"] == cached_id
