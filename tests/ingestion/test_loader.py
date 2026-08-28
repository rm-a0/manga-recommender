import uuid
from collections.abc import Generator, Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from manga_recommender.db.models.sources import Source
from manga_recommender.db.repositories.authors import bulk_get_or_create_authors
from manga_recommender.db.repositories.genres import (
    bulk_get_or_create_genres,
    create_genre,
)
from manga_recommender.db.repositories.manga import (
    bulk_add_authors_to_manga,
    bulk_add_genres_to_manga,
    create_manga,
    get_manga_by_mal_id,
)
from manga_recommender.db.repositories.manga_external_rating import (
    get_external_ratings_by_manga_and_source,
)
from manga_recommender.ingestion import loader
from manga_recommender.ingestion.base import NormalizedMangaRecord
from manga_recommender.ingestion.loader import _sync_links_for_manga, load_batch


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
    authors: list[str] | None = None,
    raw_score: float | None = None,
    votes_count: int | None = 100,
) -> NormalizedMangaRecord:
    return NormalizedMangaRecord(
        external_id=external_id,
        mal_id=mal_id,
        title=title,
        authors=authors or [],
        status=None,
        description=None,
        genres=genres,
        published_date=None,
        raw_score=raw_score,
        raw_scale_max=10.0,
        votes_count=votes_count,
        score_distribution=None,
        fetched_at=datetime.now(UTC),
    )


def _sync_genres(
    db: Session,
    cache: dict[str, uuid.UUID],
    names: set[str],
    manga_to_names: dict[uuid.UUID, Sequence[str]],
    resolve: object = None,
) -> None:
    """Call the generic link sync with the genre resolver and writer."""
    _sync_links_for_manga(
        db,
        cache,
        names,
        manga_to_names,
        resolve or bulk_get_or_create_genres,  # type: ignore[arg-type]
        bulk_add_genres_to_manga,
    )


class TestSyncLinksForManga:
    def test_attaches_genres_and_populates_the_cache(self, db_session: Session) -> None:
        manga = create_manga(db_session, title="One Piece")
        genre_cache: dict[str, uuid.UUID] = {}

        _sync_genres(
            db_session,
            genre_cache,
            {"action", "adventure"},
            {manga.id: ["action", "adventure"]},
        )

        db_session.expire_all()
        assert {genre.name for genre in manga.genres} == {"action", "adventure"}
        assert genre_cache.keys() == {"action", "adventure"}

    def test_reuses_cached_ids_without_a_bulk_lookup(self, db_session: Session) -> None:
        manga = create_manga(db_session, title="Berserk")
        genre = create_genre(db_session, name="dark fantasy")
        genre_cache = {"dark fantasy": genre.id}

        def _fail_if_called(*_args: object, **_kwargs: object) -> None:
            raise AssertionError("the resolver should not be called")

        _sync_genres(
            db_session,
            genre_cache,
            {"dark fantasy"},
            {manga.id: ["dark fantasy"]},
            resolve=_fail_if_called,
        )

        db_session.expire_all()
        assert [g.id for g in manga.genres] == [genre.id]

    def test_does_not_duplicate_existing_links(self, db_session: Session) -> None:
        manga = create_manga(db_session, title="Vagabond")
        genre_cache: dict[str, uuid.UUID] = {}
        _sync_genres(db_session, genre_cache, {"action"}, {manga.id: ["action"]})

        _sync_genres(
            db_session,
            genre_cache,
            {"action", "drama"},
            {manga.id: ["action", "drama"]},
        )

        db_session.expire_all()
        assert {genre.name for genre in manga.genres} == {"action", "drama"}

    def test_attaches_authors(self, db_session: Session) -> None:
        manga = create_manga(db_session, title="Pluto")
        author_cache: dict[str, uuid.UUID] = {}

        _sync_links_for_manga(
            db_session,
            author_cache,
            {"Naoki Urasawa"},
            {manga.id: ["Naoki Urasawa"]},
            bulk_get_or_create_authors,
            bulk_add_authors_to_manga,
        )

        db_session.expire_all()
        assert [author.name for author in manga.authors] == ["Naoki Urasawa"]


class TestLoadBatch:
    def test_creates_manga_genres_authors_and_ratings(
        self, patched_session_scope: Session, test_source: Source
    ) -> None:
        records = [
            _record(
                "1",
                mal_id=101,
                title="Chainsaw Man",
                genres=["Action", "Horror"],
                authors=["Tatsuki Fujimoto"],
            ),
            _record("2", mal_id=None, title="No Mal Id Manga", genres=["Drama"]),
        ]

        load_batch(records, test_source.id, genre_cache={}, author_cache={})

        manga_with_mal_id = get_manga_by_mal_id(patched_session_scope, 101)
        assert manga_with_mal_id is not None
        assert manga_with_mal_id.title == "Chainsaw Man"
        assert {g.name for g in manga_with_mal_id.genres} == {"action", "horror"}
        assert [a.name for a in manga_with_mal_id.authors] == ["Tatsuki Fujimoto"]

        ratings = get_external_ratings_by_manga_and_source(
            patched_session_scope, manga_with_mal_id.id, test_source.id
        )
        assert len(ratings) == 1
        assert ratings[0].votes_count == 100

    def test_upserts_existing_manga_by_mal_id(
        self, patched_session_scope: Session, test_source: Source
    ) -> None:
        load_batch(
            [_record("1", mal_id=202, title="Old Title")],
            test_source.id,
            genre_cache={},
            author_cache={},
        )

        load_batch(
            [_record("1", mal_id=202, title="New Title")],
            test_source.id,
            genre_cache={},
            author_cache={},
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
            author_cache={},
        )
        cached_id = genre_cache["action"]

        load_batch(
            [_record("2", mal_id=304, genres=["Action"])],
            test_source.id,
            genre_cache,
            author_cache={},
        )

        assert genre_cache["action"] == cached_id

    def test_highest_votes_wins_when_entries_share_a_mal_id(
        self, patched_session_scope: Session, test_source: Source
    ) -> None:
        """Two source entries, one mal_id: the metadata of the busier one sticks."""
        records = [
            _record("1", mal_id=404, title="Loser Title", votes_count=10),
            _record("2", mal_id=404, title="Winner Title", votes_count=5_000),
            _record("3", mal_id=404, title="Middle Title", votes_count=900),
        ]

        load_batch(records, test_source.id, genre_cache={}, author_cache={})

        manga = get_manga_by_mal_id(patched_session_scope, 404)
        assert manga is not None
        assert manga.title == "Winner Title"

        # Every entry still keeps its own rating row.
        ratings = get_external_ratings_by_manga_and_source(
            patched_session_scope, manga.id, test_source.id
        )
        assert {r.external_id for r in ratings} == {"1", "2", "3"}

    def test_null_votes_never_beat_a_real_count(
        self, patched_session_scope: Session, test_source: Source
    ) -> None:
        records = [
            _record("1", mal_id=505, title="Winner Title", votes_count=1),
            _record("2", mal_id=505, title="Loser Title", votes_count=None),
        ]

        load_batch(records, test_source.id, genre_cache={}, author_cache={})

        manga = get_manga_by_mal_id(patched_session_scope, 505)
        assert manga is not None
        assert manga.title == "Winner Title"


def test_zero_votes_wins_over_a_missing_count(
    patched_session_scope: Session, test_source: Source
) -> None:
    """Zero votes is a reported count; None is no data. The reported one wins."""
    records = [
        _record("1", mal_id=606, title="Loser Title", votes_count=None),
        _record("2", mal_id=606, title="Winner Title", votes_count=0),
    ]

    load_batch(records, test_source.id, genre_cache={}, author_cache={})

    manga = get_manga_by_mal_id(patched_session_scope, 606)
    assert manga is not None
    assert manga.title == "Winner Title"
