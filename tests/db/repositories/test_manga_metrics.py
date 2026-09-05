import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from manga_recommender.db.models.manga_metrics import MangaMetric
from manga_recommender.db.repositories.manga import create_manga, delete_manga
from manga_recommender.db.repositories.manga_metrics import (
    MetricValues,
    bulk_create_manga_metrics,
    delete_all_manga_metrics,
    get_manga_metric_by_manga_id,
    update_or_create_manga_metric,
)


def _metric_values(
    *,
    manga_id: uuid.UUID,
    bayesian_score: float = 0.8,
    mean_score: float = 0.85,
    votes_count: int = 1000,
    source_count: int = 2,
) -> MetricValues:
    """Build one MetricValues row with plausible defaults."""
    return MetricValues(
        manga_id=manga_id,
        bayesian_score=bayesian_score,
        mean_score=mean_score,
        votes_count=votes_count,
        source_count=source_count,
        computed_at=datetime.now(UTC),
    )


def _all_metrics(db_session: Session) -> list[MangaMetric]:
    """Reload every metric row straight from the database."""
    db_session.expire_all()
    return list(db_session.scalars(select(MangaMetric)))


def test_bulk_create_persists_every_row(db_session: Session) -> None:
    manga_ids = [create_manga(db_session, title=f"Manga {i}").id for i in range(3)]

    bulk_create_manga_metrics(
        db_session, [_metric_values(manga_id=mid) for mid in manga_ids]
    )

    stored = _all_metrics(db_session)
    assert {m.manga_id for m in stored} == set(manga_ids)


def test_bulk_create_generates_a_distinct_primary_key_per_row(
    db_session: Session,
) -> None:
    """The UUID default on Base must fire once per row, not once per statement."""
    manga_ids = [create_manga(db_session, title=f"Manga {i}").id for i in range(5)]

    bulk_create_manga_metrics(
        db_session, [_metric_values(manga_id=mid) for mid in manga_ids]
    )

    ids = [m.id for m in _all_metrics(db_session)]
    assert len(ids) == 5
    assert len(set(ids)) == 5
    assert all(i is not None for i in ids)


def test_bulk_create_round_trips_every_column(db_session: Session) -> None:
    manga = create_manga(db_session, title="Berserk")
    computed_at = datetime.now(UTC)

    bulk_create_manga_metrics(
        db_session,
        [
            MetricValues(
                manga_id=manga.id,
                bayesian_score=0.941,
                mean_score=0.947,
                votes_count=40012,
                source_count=2,
                computed_at=computed_at,
            )
        ],
    )

    stored = get_manga_metric_by_manga_id(db_session, manga.id)
    assert stored is not None
    assert stored.bayesian_score == pytest.approx(0.941)
    assert stored.mean_score == pytest.approx(0.947)
    assert stored.votes_count == 40012
    assert stored.source_count == 2
    assert stored.computed_at == computed_at


def test_bulk_create_accepts_an_empty_batch(db_session: Session) -> None:
    """An empty batch is a no-op, not an error.

    The fill stage chunks its rows. A catalogue with no usable rating
    produces no chunks, and the final chunk can come out empty.
    """
    bulk_create_manga_metrics(db_session, [])

    assert _all_metrics(db_session) == []


def test_delete_all_returns_the_number_removed(db_session: Session) -> None:
    manga_ids = [create_manga(db_session, title=f"Manga {i}").id for i in range(4)]
    bulk_create_manga_metrics(
        db_session, [_metric_values(manga_id=mid) for mid in manga_ids]
    )

    removed = delete_all_manga_metrics(db_session)

    assert removed == 4
    assert _all_metrics(db_session) == []


def test_delete_all_on_an_empty_table_returns_zero(db_session: Session) -> None:
    assert delete_all_manga_metrics(db_session) == 0


def test_deleting_a_manga_deletes_its_metric_row(db_session: Session) -> None:
    """The foreign key must cascade, or pruning an orphan hits a FK violation."""
    manga = create_manga(db_session, title="Doomed")
    bulk_create_manga_metrics(db_session, [_metric_values(manga_id=manga.id)])

    delete_manga(db_session, manga)
    db_session.flush()

    assert _all_metrics(db_session) == []


def test_get_by_manga_id_returns_none_when_unrated(db_session: Session) -> None:
    manga = create_manga(db_session, title="Unrated")

    assert get_manga_metric_by_manga_id(db_session, manga.id) is None


def test_update_or_create_creates_then_overwrites_one_row(
    db_session: Session,
) -> None:
    manga = create_manga(db_session, title="One Piece")

    update_or_create_manga_metric(
        db_session,
        manga_id=manga.id,
        bayesian_score=0.5,
        mean_score=0.5,
        votes_count=10,
        source_count=1,
        computed_at=datetime.now(UTC),
    )
    update_or_create_manga_metric(
        db_session,
        manga_id=manga.id,
        bayesian_score=0.9,
        mean_score=0.95,
        votes_count=9000,
        source_count=2,
        computed_at=datetime.now(UTC),
    )

    stored = _all_metrics(db_session)
    assert len(stored) == 1
    assert stored[0].bayesian_score == pytest.approx(0.9)
    assert stored[0].votes_count == 9000
