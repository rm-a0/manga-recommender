"""Tests for the content candidate source."""

import uuid
from collections.abc import Callable

from sqlalchemy.orm import Session

from manga_recommender.db.models.manga import Manga
from manga_recommender.recommender.base import Candidate, RecommendationQuery
from manga_recommender.recommender.candidate_sources.content import (
    ContentCandidateSource,
)
from tests.recommender.queries import make_query


def _query(*liked: uuid.UUID) -> RecommendationQuery:
    return make_query(liked_ids=liked, source_weights={"content": 1.0})


def _ids(candidates: list[Candidate]) -> list[uuid.UUID]:
    return [candidate.manga_id for candidate in candidates]


def test_get_candidates_returns_the_nearest_manga_first(
    db_session: Session,
    embedded_manga: Callable[[str, float], Manga],
) -> None:
    seed = embedded_manga("Seed", 0)
    near = embedded_manga("Near", 5)
    far = embedded_manga("Far", 60)

    candidates = ContentCandidateSource().get_candidates(
        db_session, _query(seed.id), 10
    )

    assert _ids(candidates) == [near.id, far.id]


def test_get_candidates_drops_the_liked_manga(
    db_session: Session,
    embedded_manga: Callable[[str, float], Manga],
) -> None:
    first_seed = embedded_manga("First Seed", 0)
    second_seed = embedded_manga("Second Seed", 5)
    match = embedded_manga("Match", 10)

    candidates = ContentCandidateSource().get_candidates(
        db_session, _query(first_seed.id, second_seed.id), 10
    )

    assert _ids(candidates) == [match.id]


def test_get_candidates_takes_one_match_of_each_seed_per_rank(
    db_session: Session,
    embedded_manga: Callable[[str, float], Manga],
) -> None:
    first_seed = embedded_manga("First Seed", 0)
    second_seed = embedded_manga("Second Seed", 90)
    first_match = embedded_manga("First Match", 5)
    second_match = embedded_manga("Second Match", 85)
    shared_match = embedded_manga("Shared Match", 45)

    candidates = ContentCandidateSource().get_candidates(
        db_session, _query(first_seed.id, second_seed.id), 10
    )

    # Rank 0 takes the best match of each seed, and rank 1 reaches the match
    # that both seeds nominate.
    assert _ids(candidates) == [first_match.id, second_match.id, shared_match.id]


def test_get_candidates_records_one_reason_per_nominating_seed(
    db_session: Session,
    embedded_manga: Callable[[str, float], Manga],
) -> None:
    first_seed = embedded_manga("First Seed", 0)
    second_seed = embedded_manga("Second Seed", 90)
    shared_match = embedded_manga("Shared Match", 45)

    candidates = ContentCandidateSource().get_candidates(
        db_session, _query(first_seed.id, second_seed.id), 10
    )

    shared = next(c for c in candidates if c.manga_id == shared_match.id)
    assert {reason.seed_id for reason in shared.reasons} == {
        first_seed.id,
        second_seed.id,
    }
    assert {reason.source for reason in shared.reasons} == {"content"}


def test_get_candidates_skips_a_seed_without_an_embedding(
    db_session: Session,
    embedded_manga: Callable[[str, float], Manga],
    plain_manga: Callable[[str], Manga],
) -> None:
    embedded_seed = embedded_manga("Embedded Seed", 0)
    bare_seed = plain_manga("Bare Seed")
    match = embedded_manga("Match", 5)

    candidates = ContentCandidateSource().get_candidates(
        db_session, _query(embedded_seed.id, bare_seed.id), 10
    )

    assert _ids(candidates) == [match.id]


def test_get_candidates_returns_nothing_without_seeds(db_session: Session) -> None:
    assert ContentCandidateSource().get_candidates(db_session, _query(), 10) == []


def test_get_candidates_returns_at_most_k(
    db_session: Session,
    embedded_manga: Callable[[str, float], Manga],
) -> None:
    seed = embedded_manga("Seed", 0)
    for degrees in (5, 10, 15, 20):
        embedded_manga(f"Match {degrees}", degrees)

    candidates = ContentCandidateSource().get_candidates(db_session, _query(seed.id), 2)

    assert len(candidates) == 2
