from datetime import UTC, datetime

from sqlalchemy.orm import Session

from manga_recommender.db.models.sources import Source
from manga_recommender.db.repositories.manga import create_manga
from manga_recommender.db.repositories.manga_external_rating import (
    create_external_rating,
    get_external_rating_by_manga_and_source,
    update_external_rating,
    update_or_create_external_rating,
)


def test_create_external_rating_persists_given_fields(
    db_session: Session, test_source: Source
) -> None:
    manga = create_manga(db_session, title="One Piece", author="Eiichiro Oda")

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


def test_get_external_rating_by_manga_and_source_returns_matching_rating(
    db_session: Session, test_source: Source
) -> None:
    manga = create_manga(db_session, title="Berserk", author="Kentaro Miura")
    created = create_external_rating(
        db_session,
        manga_id=manga.id,
        source_id=test_source.id,
        external_id="ext-2",
        fetched_at=datetime.now(UTC),
    )

    found = get_external_rating_by_manga_and_source(
        db_session, manga.id, test_source.id
    )

    assert found is not None
    assert found.id == created.id


def test_get_external_rating_by_manga_and_source_returns_none_when_missing(
    db_session: Session, test_source: Source
) -> None:
    manga = create_manga(db_session, title="Vagabond", author="Takehiko Inoue")

    assert (
        get_external_rating_by_manga_and_source(db_session, manga.id, test_source.id)
        is None
    )


def test_update_external_rating_overwrites_only_given_fields(
    db_session: Session, test_source: Source
) -> None:
    manga = create_manga(db_session, title="Chainsaw Man", author="Tatsuki Fujimoto")
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
    manga = create_manga(db_session, title="Dandadan", author="Yukinobu Tatsu")

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
    manga = create_manga(db_session, title="Oyasumi Punpun", author="Inio Asano")
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
