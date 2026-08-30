import uuid
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

import pytest
from sqlalchemy import Row, select
from sqlalchemy.orm import Session

from manga_recommender.db.models.sources import Source
from manga_recommender.db.models.tags import manga_tags
from manga_recommender.db.repositories.manga import (
    create_manga,
    get_manga_by_mal_id,
)
from manga_recommender.db.repositories.manga_external_rating import (
    get_external_ratings_by_manga_and_source,
)
from manga_recommender.db.repositories.tags import create_tag
from manga_recommender.ingestion import loader
from manga_recommender.ingestion.base import NormalizedMangaRecord, NormalizedTag
from manga_recommender.ingestion.loader import (
    _sync_authors_for_manga,
    _sync_tags_for_manga,
    load_batch,
)


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


def _tag(
    name: str,
    *,
    category: str | None = None,
    rank: int | None = None,
    is_spoiler: bool = False,
) -> NormalizedTag:
    return NormalizedTag(name=name, category=category, rank=rank, is_spoiler=is_spoiler)


def _record(
    external_id: str,
    *,
    mal_id: int | None = None,
    title: str = "Test Manga",
    tags: list[NormalizedTag] | None = None,
    authors: list[str] | None = None,
    raw_score: float | None = None,
    votes_count: int | None = 100,
    image_url: str | None = None,
) -> NormalizedMangaRecord:
    return NormalizedMangaRecord(
        external_id=external_id,
        mal_id=mal_id,
        title=title,
        authors=authors or [],
        status=None,
        description=None,
        tags=tags,
        published_date=None,
        raw_score=raw_score,
        raw_scale_max=10.0,
        votes_count=votes_count,
        score_distribution=None,
        fetched_at=datetime.now(UTC),
        image_url=image_url,
    )


def _link(db: Session, manga_id: uuid.UUID, tag_id: uuid.UUID) -> Row:
    """Return the manga_tags row for one pairing."""
    db.expire_all()
    return db.execute(
        select(manga_tags).where(
            manga_tags.c.manga_id == manga_id,
            manga_tags.c.tag_id == tag_id,
        )
    ).one()


class TestSyncTagsForManga:
    def test_attaches_tags_and_populates_the_cache(self, db_session: Session) -> None:
        manga = create_manga(db_session, title="One Piece")
        tag_cache: dict[str, uuid.UUID] = {}

        _sync_tags_for_manga(
            db_session,
            tag_cache,
            {manga.id: [_tag("Action"), _tag("Adventure")]},
        )

        db_session.expire_all()
        assert {tag.name for tag in manga.tags} == {"Action", "Adventure"}
        assert tag_cache.keys() == {"Action", "Adventure"}

    def test_caches_by_the_spelling_the_source_gave(self, db_session: Session) -> None:
        """Normalization happens in the repository, so the cache holds raw names."""
        manga = create_manga(db_session, title="Steins;Gate")
        tag_cache: dict[str, uuid.UUID] = {}

        _sync_tags_for_manga(db_session, tag_cache, {manga.id: [_tag("Sci-Fi")]})

        assert "Sci-Fi" in tag_cache

    def test_writes_rank_and_spoiler(self, db_session: Session) -> None:
        manga = create_manga(db_session, title="Monster")
        tag_cache: dict[str, uuid.UUID] = {}

        _sync_tags_for_manga(
            db_session,
            tag_cache,
            {manga.id: [_tag("Twist", category="Theme", rank=78, is_spoiler=True)]},
        )

        row = _link(db_session, manga.id, tag_cache["Twist"])
        assert row.rank == 78
        assert row.is_spoiler is True

    def test_reuses_cached_ids_without_a_bulk_lookup(
        self, db_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        manga = create_manga(db_session, title="Berserk")
        tag = create_tag(db_session, name="Dark Fantasy", category=None)
        tag_cache = {"Dark Fantasy": tag.id}

        def _fail_if_called(*_args: object, **_kwargs: object) -> None:
            raise AssertionError("the resolver should not be called")

        monkeypatch.setattr(loader, "bulk_get_or_create_tags", _fail_if_called)
        _sync_tags_for_manga(db_session, tag_cache, {manga.id: [_tag("Dark Fantasy")]})

        db_session.expire_all()
        assert [t.id for t in manga.tags] == [tag.id]

    def test_does_not_duplicate_existing_links(self, db_session: Session) -> None:
        manga = create_manga(db_session, title="Vagabond")
        tag_cache: dict[str, uuid.UUID] = {}
        _sync_tags_for_manga(db_session, tag_cache, {manga.id: [_tag("Action")]})

        _sync_tags_for_manga(
            db_session, tag_cache, {manga.id: [_tag("Action"), _tag("Drama")]}
        )

        db_session.expire_all()
        assert {tag.name for tag in manga.tags} == {"Action", "Drama"}

    def test_keeps_a_rank_a_second_pass_omits(self, db_session: Session) -> None:
        """A rankless re-sync must not clear the rank an earlier one wrote."""
        manga = create_manga(db_session, title="Vinland Saga")
        tag_cache: dict[str, uuid.UUID] = {}
        _sync_tags_for_manga(
            db_session, tag_cache, {manga.id: [_tag("Historical", rank=64)]}
        )

        _sync_tags_for_manga(db_session, tag_cache, {manga.id: [_tag("Historical")]})

        assert _link(db_session, manga.id, tag_cache["Historical"]).rank == 64


class TestSyncAuthorsForManga:
    def test_attaches_authors(self, db_session: Session) -> None:
        manga = create_manga(db_session, title="Pluto")
        author_cache: dict[str, uuid.UUID] = {}

        _sync_authors_for_manga(db_session, author_cache, {manga.id: ["Naoki Urasawa"]})

        db_session.expire_all()
        assert [author.name for author in manga.authors] == ["Naoki Urasawa"]


class TestLoadBatch:
    def test_creates_manga_tags_authors_and_ratings(
        self, patched_session_scope: Session, test_source: Source
    ) -> None:
        records = [
            _record(
                "1",
                mal_id=101,
                title="Chainsaw Man",
                tags=[_tag("Action", rank=90), _tag("Horror", category="Genre")],
                authors=["Tatsuki Fujimoto"],
            ),
            _record("2", mal_id=None, title="No Mal Id Manga", tags=[_tag("Drama")]),
        ]

        load_batch(records, test_source.id, tag_cache={}, author_cache={})

        manga_with_mal_id = get_manga_by_mal_id(patched_session_scope, 101)
        assert manga_with_mal_id is not None
        assert manga_with_mal_id.title == "Chainsaw Man"
        assert {t.name for t in manga_with_mal_id.tags} == {"Action", "Horror"}
        assert [a.name for a in manga_with_mal_id.authors] == ["Tatsuki Fujimoto"]

        ratings = get_external_ratings_by_manga_and_source(
            patched_session_scope, manga_with_mal_id.id, test_source.id
        )
        assert len(ratings) == 1
        assert ratings[0].votes_count == 100

    def test_keeps_the_spelling_the_source_gave(
        self, patched_session_scope: Session, test_source: Source
    ) -> None:
        """The loader no longer lowercases; the repository owns normalization."""
        load_batch(
            [_record("1", mal_id=707, tags=[_tag("Slice of Life")])],
            test_source.id,
            tag_cache={},
            author_cache={},
        )

        manga = get_manga_by_mal_id(patched_session_scope, 707)
        assert manga is not None
        assert [t.name for t in manga.tags] == ["Slice of Life"]

    def test_upserts_existing_manga_by_mal_id(
        self, patched_session_scope: Session, test_source: Source
    ) -> None:
        load_batch(
            [_record("1", mal_id=202, title="Old Title")],
            test_source.id,
            tag_cache={},
            author_cache={},
        )

        load_batch(
            [_record("1", mal_id=202, title="New Title")],
            test_source.id,
            tag_cache={},
            author_cache={},
        )

        manga = get_manga_by_mal_id(patched_session_scope, 202)
        assert manga is not None
        assert manga.title == "New Title"

    def test_persists_the_image_url(
        self, patched_session_scope: Session, test_source: Source
    ) -> None:
        load_batch(
            [_record("1", mal_id=808, image_url="https://cdn.test/808.jpg")],
            test_source.id,
            tag_cache={},
            author_cache={},
        )

        manga = get_manga_by_mal_id(patched_session_scope, 808)
        assert manga is not None
        assert manga.image_url == "https://cdn.test/808.jpg"

    def test_keeps_an_image_url_a_later_batch_omits(
        self, patched_session_scope: Session, test_source: Source
    ) -> None:
        """A source without cover art must not blank one another source gave."""
        load_batch(
            [_record("1", mal_id=809, image_url="https://cdn.test/809.jpg")],
            test_source.id,
            tag_cache={},
            author_cache={},
        )

        load_batch(
            [_record("1", mal_id=809, title="Second Pass", image_url=None)],
            test_source.id,
            tag_cache={},
            author_cache={},
        )

        manga = get_manga_by_mal_id(patched_session_scope, 809)
        assert manga is not None
        assert manga.title == "Second Pass"
        assert manga.image_url == "https://cdn.test/809.jpg"

    def test_shares_the_tag_cache_across_calls(
        self, patched_session_scope: Session, test_source: Source
    ) -> None:
        tag_cache: dict[str, uuid.UUID] = {}
        load_batch(
            [_record("1", mal_id=303, tags=[_tag("Action")])],
            test_source.id,
            tag_cache,
            author_cache={},
        )
        cached_id = tag_cache["Action"]

        load_batch(
            [_record("2", mal_id=304, tags=[_tag("Action")])],
            test_source.id,
            tag_cache,
            author_cache={},
        )

        assert tag_cache["Action"] == cached_id

    def test_highest_votes_wins_when_entries_share_a_mal_id(
        self, patched_session_scope: Session, test_source: Source
    ) -> None:
        """Two source entries, one mal_id: the metadata of the busier one sticks."""
        records = [
            _record("1", mal_id=404, title="Loser Title", votes_count=10),
            _record("2", mal_id=404, title="Winner Title", votes_count=5_000),
            _record("3", mal_id=404, title="Middle Title", votes_count=900),
        ]

        load_batch(records, test_source.id, tag_cache={}, author_cache={})

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

        load_batch(records, test_source.id, tag_cache={}, author_cache={})

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

    load_batch(records, test_source.id, tag_cache={}, author_cache={})

    manga = get_manga_by_mal_id(patched_session_scope, 606)
    assert manga is not None
    assert manga.title == "Winner Title"
