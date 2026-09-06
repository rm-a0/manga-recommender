import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from manga_recommender.db.models.sources import Source
from manga_recommender.db.repositories.manga import create_manga
from manga_recommender.db.repositories.manga_external_rating import (
    create_external_rating,
)
from manga_recommender.pipeline.stages.fill import (
    _compute_bayesian_average,
    _compute_catalogue_mean,
    _compute_mean,
    compute_manga_metrics,
)

CATALOGUE_MEAN = 0.7


def _aggregate_row(numerator: float, denominator: float) -> SimpleNamespace:
    """Stand in for one row of `get_rating_aggregates`."""
    return SimpleNamespace(
        weighted_numerator=numerator, weighted_denominator=denominator
    )


def _rate(
    db_session: Session,
    source: Source,
    title: str,
    *,
    raw_score: float,
    votes_count: int,
) -> uuid.UUID:
    """Create one manga with a single rating and return its id."""
    manga = create_manga(db_session, title=title)
    create_external_rating(
        db_session,
        manga_id=manga.id,
        source_id=source.id,
        external_id=title,
        raw_score=raw_score,
        raw_scale_max=10.0,
        votes_count=votes_count,
        fetched_at=datetime.now(UTC),
    )
    return manga.id


def test_bayesian_average_returns_the_catalogue_mean_without_votes() -> None:
    assert _compute_bayesian_average(
        weighted_numerator=0.0,
        weighted_denominator=0.0,
        catalogue_mean=CATALOGUE_MEAN,
        smoothing_votes=500.0,
    ) == pytest.approx(CATALOGUE_MEAN)


def test_bayesian_average_returns_the_manga_mean_when_votes_dominate() -> None:
    score = _compute_bayesian_average(
        weighted_numerator=0.9 * 10_000_000,
        weighted_denominator=10_000_000,
        catalogue_mean=CATALOGUE_MEAN,
        smoothing_votes=500.0,
    )

    assert score == pytest.approx(0.9, abs=1e-4)


def test_bayesian_average_returns_the_midpoint_when_votes_equal_the_smoothing() -> None:
    # The break-even point: the manga's own mean and the catalogue mean each
    # carry half the weight.
    score = _compute_bayesian_average(
        weighted_numerator=0.9 * 500.0,
        weighted_denominator=500.0,
        catalogue_mean=CATALOGUE_MEAN,
        smoothing_votes=500.0,
    )

    assert score == pytest.approx((0.9 + CATALOGUE_MEAN) / 2)


def test_compute_mean_divides_the_weighted_sums() -> None:
    assert _compute_mean(170.0, 200.0) == pytest.approx(0.85)


def test_catalogue_mean_pools_every_vote_instead_of_averaging_manga() -> None:
    # One tiny high scorer and one huge low scorer. Averaging the two manga
    # would give 0.5; pooling the votes gives a number near the popular one.
    rows = [_aggregate_row(9.0, 10.0), _aggregate_row(100.0, 1000.0)]

    assert _compute_catalogue_mean(rows) == pytest.approx(109.0 / 1010.0)


def test_compute_manga_metrics_returns_nothing_when_no_manga_is_rated(
    db_session: Session,
) -> None:
    create_manga(db_session, title="Nobody rated me")

    assert compute_manga_metrics(db_session, smoothing_votes=500.0) == []


def test_compute_manga_metrics_carries_the_aggregate_counts_through(
    db_session: Session, test_source: Source
) -> None:
    manga_id = _rate(
        db_session, test_source, "Berserk", raw_score=9.0, votes_count=1234
    )

    rows = compute_manga_metrics(db_session, smoothing_votes=500.0)

    assert len(rows) == 1
    assert rows[0]["manga_id"] == manga_id
    assert rows[0]["votes_count"] == 1234
    assert rows[0]["source_count"] == 1
    assert rows[0]["mean_score"] == pytest.approx(0.9)


def test_compute_manga_metrics_stamps_every_row_with_one_timestamp(
    db_session: Session, test_source: Source
) -> None:
    _rate(db_session, test_source, "Berserk", raw_score=9.0, votes_count=100)
    _rate(db_session, test_source, "Monster", raw_score=8.0, votes_count=200)

    rows = compute_manga_metrics(db_session, smoothing_votes=500.0)

    assert len(rows) == 2
    assert len({row["computed_at"] for row in rows}) == 1
    assert rows[0]["computed_at"].tzinfo is not None


def test_compute_manga_metrics_ranks_a_lightly_rated_manga_below_a_popular_one(
    db_session: Session, test_source: Source
) -> None:
    # The obscure manga has the better raw score. Shrinkage must still put the
    # popular one above it, because ten votes are not evidence.
    obscure_id = _rate(
        db_session, test_source, "Obscure", raw_score=9.5, votes_count=10
    )
    popular_id = _rate(
        db_session, test_source, "Popular", raw_score=8.5, votes_count=40_000
    )
    _rate(db_session, test_source, "Filler", raw_score=6.0, votes_count=100_000)

    by_id = {
        row["manga_id"]: row
        for row in compute_manga_metrics(db_session, smoothing_votes=500.0)
    }
    obscure, popular = by_id[obscure_id], by_id[popular_id]

    assert obscure["mean_score"] > popular["mean_score"]
    assert obscure["bayesian_score"] < popular["bayesian_score"]
    # The obscure manga barely moves off the catalogue mean of ~0.671.
    assert obscure["bayesian_score"] == pytest.approx(0.6769, abs=1e-3)
    assert popular["bayesian_score"] == pytest.approx(0.8478, abs=1e-3)
