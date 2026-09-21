"""Tests for the scorer and the selector."""

import uuid

from manga_recommender.recommender.base import Candidate, RecommendationQuery
from manga_recommender.recommender.scorers.rank_fusion import (
    _RANK_CONSTANT,
    weighted_rank_fusion,
)
from manga_recommender.recommender.selectors.top_k import take_top_k


def _query(**overrides: object) -> RecommendationQuery:
    fields: dict[str, object] = {
        "liked_ids": (),
        "disliked_ids": (),
        "source_weights": {"content": 1.0},
    }
    fields.update(overrides)
    return RecommendationQuery(**fields)  # type: ignore[arg-type]


def _candidate(score: float = 0.0, **source_ranks: int) -> Candidate:
    return Candidate(manga_id=uuid.uuid4(), source_ranks=source_ranks, score=score)


def test_weighted_rank_fusion_scores_a_better_rank_higher() -> None:
    first, second = _candidate(content=0), _candidate(content=1)

    weighted_rank_fusion(_query(), [first, second])

    assert first.score > second.score


def test_weighted_rank_fusion_applies_the_rank_constant() -> None:
    candidate = _candidate(content=0)

    weighted_rank_fusion(_query(), [candidate])

    assert candidate.score == 1 / _RANK_CONSTANT


def test_weighted_rank_fusion_weights_each_source() -> None:
    weak, strong = _candidate(weak_source=0), _candidate(strong_source=0)
    query = _query(source_weights={"weak_source": 0.5, "strong_source": 2.0})

    weighted_rank_fusion(query, [weak, strong])

    assert strong.score == 4 * weak.score


def test_weighted_rank_fusion_adds_the_score_of_every_source() -> None:
    both = _candidate(content=0, tags=0)
    one = _candidate(content=0)
    query = _query(source_weights={"content": 1.0, "tags": 1.0})

    weighted_rank_fusion(query, [both, one])

    assert both.score == 2 * one.score


def test_weighted_rank_fusion_scores_a_candidate_of_no_source_zero() -> None:
    candidate = _candidate()

    weighted_rank_fusion(_query(), [candidate])

    assert candidate.score == 0.0


def test_take_top_k_orders_by_score() -> None:
    low, high = _candidate(score=0.1), _candidate(score=0.9)

    result = take_top_k(_query(), [low, high])

    assert result == [high, low]


def test_take_top_k_cuts_the_list_to_the_limit() -> None:
    candidates = [_candidate(score=float(index)) for index in range(5)]

    result = take_top_k(_query(limit=2), candidates)

    assert [c.score for c in result] == [4.0, 3.0]


def test_take_top_k_keeps_the_given_order_of_equal_scores() -> None:
    first, second = _candidate(score=0.5), _candidate(score=0.5)

    result = take_top_k(_query(), [first, second])

    assert result == [first, second]
