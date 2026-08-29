"""Regression tests for issues found while reviewing commits 9a5a142 and 49dc21f.

Each test pins one fixed defect: a dropped column in an update, an upsert that
keyed on the wrong columns, missing delete cascades, a bulk insert that broke on
repeated names, and naive timestamp columns.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from manga_recommender.db.models.manga import Manga
from manga_recommender.db.models.manga_external_ratings import MangaExternalRating
from manga_recommender.db.models.sources import Source
from manga_recommender.db.repositories.authors import bulk_get_or_create_authors
from manga_recommender.db.repositories.manga import (
    TagLinkValues,
    bulk_add_authors_to_manga,
    bulk_add_tags_to_manga,
    create_manga,
    delete_manga,
    delete_orphaned_manga,
)
from manga_recommender.db.repositories.manga_external_rating import (
    create_external_rating,
    update_external_rating,
    update_or_create_external_rating,
)
from manga_recommender.db.repositories.tags import (
    TagUpsertValues,
    bulk_get_or_create_tags,
)

# --- Finding 2: update_external_rating drops score_distribution ---


def test_update_external_rating_persists_score_distribution(
    db_session: Session, test_source: Source
) -> None:
    """The signature accepts score_distribution, so the update must store it."""
    manga = create_manga(db_session, title="Berserk")
    rating = create_external_rating(
        db_session,
        manga_id=manga.id,
        source_id=test_source.id,
        external_id="ext-1",
        fetched_at=datetime.now(UTC),
        score_distribution=[1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    )

    update_external_rating(
        db_session,
        rating,
        score_distribution=[0, 0, 0, 0, 0, 0, 0, 0, 0, 99],
    )

    db_session.expire_all()
    assert rating.score_distribution == [0, 0, 0, 0, 0, 0, 0, 0, 0, 99]


# --- Finding 1: the single-row upsert still assumes (manga_id, source_id) is unique ---


def test_update_or_create_external_rating_targets_the_matching_external_id(
    db_session: Session, test_source: Source
) -> None:
    """One manga can hold two ratings from one source, so external_id picks the row."""
    manga = create_manga(db_session, title="Vagabond")
    first = create_external_rating(
        db_session,
        manga_id=manga.id,
        source_id=test_source.id,
        external_id="ext-a",
        raw_score=10.0,
        fetched_at=datetime.now(UTC),
    )
    second = create_external_rating(
        db_session,
        manga_id=manga.id,
        source_id=test_source.id,
        external_id="ext-b",
        raw_score=20.0,
        fetched_at=datetime.now(UTC),
    )

    updated = update_or_create_external_rating(
        db_session,
        manga_id=manga.id,
        source_id=test_source.id,
        external_id="ext-b",
        raw_score=99.0,
        fetched_at=datetime.now(UTC),
    )

    assert updated.id == second.id, "upsert hit the wrong row for this external_id"
    db_session.expire_all()
    assert first.raw_score == 10.0


def test_update_or_create_external_rating_creates_a_second_row_per_external_id(
    db_session: Session, test_source: Source
) -> None:
    """A new external_id under an existing manga and source must insert, not update."""
    manga = create_manga(db_session, title="Monster")
    first = create_external_rating(
        db_session,
        manga_id=manga.id,
        source_id=test_source.id,
        external_id="ext-a",
        raw_score=10.0,
        fetched_at=datetime.now(UTC),
    )

    second = update_or_create_external_rating(
        db_session,
        manga_id=manga.id,
        source_id=test_source.id,
        external_id="ext-b",
        raw_score=20.0,
        fetched_at=datetime.now(UTC),
    )

    assert second.id != first.id
    db_session.expire_all()
    assert first.raw_score == 10.0


# --- Finding 7: no ON DELETE on the child foreign keys ---


def test_delete_manga_removes_its_external_ratings(
    db_session: Session, test_source: Source
) -> None:
    """Deleting a manga must not fail on its rating rows."""
    manga = create_manga(db_session, title="Pluto")
    create_external_rating(
        db_session,
        manga_id=manga.id,
        source_id=test_source.id,
        external_id="ext-1",
        fetched_at=datetime.now(UTC),
    )

    delete_manga(db_session, manga)

    db_session.expire_all()
    remaining = db_session.scalars(
        select(MangaExternalRating).where(MangaExternalRating.manga_id == manga.id)
    ).all()
    assert remaining == []


def test_delete_manga_removes_its_tag_links(db_session: Session) -> None:
    """Deleting a manga must not fail on its manga_tags rows."""
    manga = create_manga(db_session, title="Blame!")
    tag_ids = bulk_get_or_create_tags(
        db_session, [TagUpsertValues(name="cyberpunk", category=None)]
    )
    bulk_add_tags_to_manga(
        db_session,
        [
            TagLinkValues(
                manga_id=manga.id,
                tag_id=tag_ids["cyberpunk"],
                rank=None,
                is_spoiler=False,
            )
        ],
    )

    delete_manga(db_session, manga)


# --- Finding "minor": bulk_get_or_create_tags does not deduplicate its input ---


def test_bulk_get_or_create_tags_tolerates_duplicate_names(
    db_session: Session,
) -> None:
    """Duplicate names in one call must collapse, not raise CardinalityViolation."""
    result = bulk_get_or_create_tags(
        db_session,
        [
            TagUpsertValues(name="seinen", category=None),
            TagUpsertValues(name="seinen", category=None),
            TagUpsertValues(name="josei", category=None),
        ],
    )

    assert set(result) == {"seinen", "josei"}


# --- Finding 6: timestamp columns drop the time zone ---


@pytest.mark.parametrize(
    ("table", "column"),
    [
        ("manga_external_ratings", "fetched_at"),
        ("manga", "published_date"),
    ],
)
def test_timestamp_columns_keep_their_time_zone(
    db_session: Session, table: str, column: str
) -> None:
    """Aware datetimes go in, so the columns must be TIMESTAMP WITH TIME ZONE."""
    columns = inspect(db_session.get_bind()).get_columns(table)
    column_type = next(c["type"] for c in columns if c["name"] == column)

    assert getattr(column_type, "timezone", False), f"{table}.{column} is naive"


def test_fetched_at_round_trips_as_an_aware_datetime(
    db_session: Session, test_source: Source
) -> None:
    """A rating written with an aware datetime must read back aware."""
    manga = create_manga(db_session, title="Dorohedoro")
    rating = create_external_rating(
        db_session,
        manga_id=manga.id,
        source_id=test_source.id,
        external_id="ext-1",
        fetched_at=datetime.now(UTC),
    )

    db_session.expire_all()
    assert rating.fetched_at.tzinfo is not None


# --- Finding 1 (schema half): the natural key must still be enforced ---


def test_source_and_external_id_stay_unique(
    db_session: Session, test_source: Source
) -> None:
    """Dropping the manga/source constraint must leave the natural key in place."""
    first = create_manga(db_session, title="Gantz")
    second = create_manga(db_session, title="Gantz G")
    create_external_rating(
        db_session,
        manga_id=first.id,
        source_id=test_source.id,
        external_id="dup",
        fetched_at=datetime.now(UTC),
    )

    with pytest.raises(IntegrityError):
        create_external_rating(
            db_session,
            manga_id=second.id,
            source_id=test_source.id,
            external_id="dup",
            fetched_at=datetime.now(UTC),
        )


# --- delete_orphaned_manga only looks at whether a rating row exists ---


def test_orphan_prune_keeps_manga_whose_rating_has_no_score_or_votes(
    db_session: Session, test_source: Source
) -> None:
    """A rating row with nothing in it still means the manga is reachable."""
    manga = create_manga(db_session, title="Unrated But Real")
    create_external_rating(
        db_session,
        manga_id=manga.id,
        source_id=test_source.id,
        external_id="ext-1",
        fetched_at=datetime.now(UTC),
        raw_score=None,
        votes_count=0,
    )

    delete_orphaned_manga(db_session)

    db_session.expire_all()
    assert db_session.get(Manga, manga.id) is not None


def test_orphan_prune_keeps_a_description_when_a_rating_row_exists(
    db_session: Session, test_source: Source
) -> None:
    """Guards the row that semantic search would want to embed."""
    manga = create_manga(
        db_session,
        title="Descriptive",
        description="A long synopsis worth embedding.",
    )
    create_external_rating(
        db_session,
        manga_id=manga.id,
        source_id=test_source.id,
        external_id="ext-2",
        fetched_at=datetime.now(UTC),
        raw_score=None,
        votes_count=None,
    )

    delete_orphaned_manga(db_session)

    db_session.expire_all()
    assert db_session.get(Manga, manga.id) is not None


def test_orphan_prune_removes_a_manga_with_no_rating_row(
    db_session: Session,
) -> None:
    manga = create_manga(db_session, title="Left Behind")

    removed = delete_orphaned_manga(db_session)

    db_session.expire_all()
    assert removed >= 1
    assert db_session.get(Manga, manga.id) is None


def test_orphan_prune_takes_the_tag_and_author_links_with_it(
    db_session: Session,
) -> None:
    """The link rows must cascade, not block the delete."""
    manga = create_manga(db_session, title="Orphan With Links")
    tag_ids = bulk_get_or_create_tags(
        db_session, [TagUpsertValues(name="seinen", category=None)]
    )
    author_ids = bulk_get_or_create_authors(db_session, ["Naoki Urasawa"])
    bulk_add_tags_to_manga(
        db_session,
        [
            TagLinkValues(
                manga_id=manga.id,
                tag_id=tag_ids["seinen"],
                rank=None,
                is_spoiler=False,
            )
        ],
    )
    bulk_add_authors_to_manga(db_session, [(manga.id, author_ids["Naoki Urasawa"])])

    delete_orphaned_manga(db_session)

    db_session.expire_all()
    assert db_session.get(Manga, manga.id) is None
