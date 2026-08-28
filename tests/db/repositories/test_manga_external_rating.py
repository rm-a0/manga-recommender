import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from manga_recommender.db.models.manga_external_ratings import MangaExternalRating
from manga_recommender.db.models.sources import Source
from manga_recommender.db.repositories.manga import create_manga
from manga_recommender.db.repositories.manga_external_rating import (
    RatingUpsertValues,
    bulk_update_or_create_external_ratings,
    create_external_rating,
    get_external_ratings_by_manga_and_source,
    update_external_rating,
    update_or_create_external_rating,
)


def _rating_values(
    *,
    manga_id: uuid.UUID,
    source_id: uuid.UUID,
    external_id: str | None = None,
    raw_score: float | None = 7.0,
    votes_count: int | None = 100,
    raw_scale_max: float | None = 10.0,
    score_distribution: list[int] | None = None,
) -> RatingUpsertValues:
    """Build one RatingUpsertValues, defaulting external_id to str(manga_id)."""
    return RatingUpsertValues(
        manga_id=manga_id,
        source_id=source_id,
        external_id=external_id if external_id is not None else str(manga_id),
        raw_scale_max=raw_scale_max,
        votes_count=votes_count,
        fetched_at=datetime.now(UTC),
        raw_score=raw_score,
        score_distribution=score_distribution,
    )


def _ratings_for_source(
    db_session: Session, source_id: uuid.UUID
) -> list[MangaExternalRating]:
    """Reload every rating row for a source straight from the database."""
    db_session.expire_all()
    return list(
        db_session.scalars(
            select(MangaExternalRating).where(
                MangaExternalRating.source_id == source_id
            )
        )
    )


def test_create_external_rating_persists_given_fields(
    db_session: Session, test_source: Source
) -> None:
    manga = create_manga(db_session, title="One Piece")

    rating = create_external_rating(
        db_session,
        manga_id=manga.id,
        source_id=test_source.id,
        external_id="ext-1",
        raw_score=85.0,
        raw_scale_max=100.0,
        votes_count=1000,
        fetched_at=datetime.now(UTC),
    )

    assert rating.id is not None
    assert rating.manga_id == manga.id
    assert rating.source_id == test_source.id
    assert rating.raw_score == 85.0
    assert rating.votes_count == 1000


def test_get_external_ratings_by_manga_and_source_returns_every_match(
    db_session: Session, test_source: Source
) -> None:
    manga = create_manga(db_session, title="Berserk")
    created = [
        create_external_rating(
            db_session,
            manga_id=manga.id,
            source_id=test_source.id,
            external_id=external_id,
            fetched_at=datetime.now(UTC),
        )
        for external_id in ("ext-2", "ext-3")
    ]

    found = get_external_ratings_by_manga_and_source(
        db_session, manga.id, test_source.id
    )

    assert {r.id for r in found} == {r.id for r in created}


def test_get_external_ratings_by_manga_and_source_is_empty_when_missing(
    db_session: Session, test_source: Source
) -> None:
    manga = create_manga(db_session, title="Vagabond")

    assert (
        get_external_ratings_by_manga_and_source(db_session, manga.id, test_source.id)
        == []
    )


def test_update_external_rating_overwrites_only_given_fields(
    db_session: Session, test_source: Source
) -> None:
    manga = create_manga(db_session, title="Chainsaw Man")
    rating = create_external_rating(
        db_session,
        manga_id=manga.id,
        source_id=test_source.id,
        external_id="ext-3",
        raw_score=70.0,
        votes_count=500,
        fetched_at=datetime.now(UTC),
    )

    updated = update_external_rating(db_session, rating, raw_score=95.0)

    assert updated.raw_score == 95.0
    assert updated.votes_count == 500


def test_update_or_create_external_rating_creates_when_missing(
    db_session: Session, test_source: Source
) -> None:
    manga = create_manga(db_session, title="Dandadan")

    rating = update_or_create_external_rating(
        db_session,
        manga_id=manga.id,
        source_id=test_source.id,
        external_id="ext-4",
        raw_score=88.0,
        fetched_at=datetime.now(UTC),
    )

    assert rating.id is not None
    assert rating.raw_score == 88.0


def test_update_or_create_external_rating_updates_existing_rating(
    db_session: Session, test_source: Source
) -> None:
    manga = create_manga(db_session, title="Oyasumi Punpun")
    original = create_external_rating(
        db_session,
        manga_id=manga.id,
        source_id=test_source.id,
        external_id="ext-5",
        raw_score=60.0,
        fetched_at=datetime.now(UTC),
    )

    updated = update_or_create_external_rating(
        db_session,
        manga_id=manga.id,
        source_id=test_source.id,
        external_id="ext-5",
        raw_score=99.0,
        fetched_at=datetime.now(UTC),
    )

    assert updated.id == original.id
    assert updated.raw_score == 99.0


# --- bulk_update_or_create_external_ratings ---


def test_bulk_ratings_writes_one_row_per_distinct_manga(
    db_session: Session, test_source: Source
) -> None:
    mangas = [create_manga(db_session, title=f"M{i}") for i in range(3)]
    values = [
        _rating_values(manga_id=m.id, source_id=test_source.id, raw_score=float(i))
        for i, m in enumerate(mangas)
    ]

    bulk_update_or_create_external_ratings(db_session, values)

    rows = _ratings_for_source(db_session, test_source.id)
    assert sorted(r.raw_score for r in rows if r.raw_score is not None) == [
        0.0,
        1.0,
        2.0,
    ]


def test_bulk_ratings_dedupes_repeated_manga_source_last_wins(
    db_session: Session, test_source: Source
) -> None:
    manga = create_manga(db_session, title="Monster")
    values = [
        _rating_values(
            manga_id=manga.id,
            source_id=test_source.id,
            raw_score=7.0,
            votes_count=10,
        ),
        _rating_values(
            manga_id=manga.id,
            source_id=test_source.id,
            raw_score=9.0,
            votes_count=99,
        ),
    ]

    bulk_update_or_create_external_ratings(db_session, values)

    rows = _ratings_for_source(db_session, test_source.id)
    assert len(rows) == 1
    assert rows[0].raw_score == 9.0
    assert rows[0].votes_count == 99


def test_bulk_ratings_updates_existing_row_in_place(
    db_session: Session, test_source: Source
) -> None:
    manga = create_manga(db_session, title="Pluto")
    original = create_external_rating(
        db_session,
        manga_id=manga.id,
        source_id=test_source.id,
        external_id=str(manga.id),
        raw_score=5.0,
        votes_count=1,
        fetched_at=datetime.now(UTC),
    )

    bulk_update_or_create_external_ratings(
        db_session,
        [_rating_values(manga_id=manga.id, source_id=test_source.id, raw_score=8.5)],
    )

    rows = _ratings_for_source(db_session, test_source.id)
    assert len(rows) == 1
    assert rows[0].id == original.id
    assert rows[0].raw_score == 8.5
