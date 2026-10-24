"""Tests for the community candidate source."""

import uuid
from collections.abc import Callable

from sqlalchemy.orm import Session

from manga_recommender.db.models.manga import Manga
from manga_recommender.db.models.manga_similarities import SimilarityMethod
from manga_recommender.db.repositories.manga_similarities import (
    SimilarityValues,
    bulk_create_manga_similarities,
)
from manga_recommender.recommender.base import Candidate, RecommendationQuery
from manga_recommender.recommender.candidate_sources.community import (
    CommunityCandidateSource,
)
from tests.recommender.queries import make_query


def _query(*liked: uuid.UUID) -> RecommendationQuery:
    return make_query(liked_ids=liked, source_weights={"community": 1.0})


def _ids(candidates: list[Candidate]) -> list[uuid.UUID]:
    return [candidate.manga_id for candidate in candidates]


def _recommend(
    db: Session,
    seed: Manga,
    *scored: tuple[Manga, float],
    method: SimilarityMethod = SimilarityMethod.COMMUNITY_RECS,
) -> None:
    """Store one edge from `seed` to each manga in `scored`, with its score."""
    bulk_create_manga_similarities(
        db,
        [
            SimilarityValues(
                manga_id=seed.id,
                method=method,
                similar_manga_id=manga.id,
                score=score,
            )
            for manga, score in scored
        ],
    )


def test_get_candidates_returns_the_best_scored_recommendation_first(
    db_session: Session,
    plain_manga: Callable[[str], Manga],
) -> None:
    seed = plain_manga("Seed")
    weak = plain_manga("Weak")
    strong = plain_manga("Strong")
    _recommend(db_session, seed, (weak, 0.25), (strong, 0.75))

    candidates = CommunityCandidateSource().get_candidates(
        db_session, _query(seed.id), 10
    )

    assert _ids(candidates) == [strong.id, weak.id]


def test_get_candidates_ignores_edges_from_other_methods(
    db_session: Session,
    plain_manga: Callable[[str], Manga],
) -> None:
    seed = plain_manga("Seed")
    community = plain_manga("Community")
    collab = plain_manga("Collab")
    _recommend(db_session, seed, (community, 0.5))
    _recommend(db_session, seed, (collab, 0.9), method=SimilarityMethod.COLLAB)

    candidates = CommunityCandidateSource().get_candidates(
        db_session, _query(seed.id), 10
    )

    assert _ids(candidates) == [community.id]


def test_get_candidates_drops_the_liked_manga(
    db_session: Session,
    plain_manga: Callable[[str], Manga],
) -> None:
    first_seed = plain_manga("First Seed")
    second_seed = plain_manga("Second Seed")
    match = plain_manga("Match")
    _recommend(db_session, first_seed, (second_seed, 0.75), (match, 0.25))

    candidates = CommunityCandidateSource().get_candidates(
        db_session, _query(first_seed.id, second_seed.id), 10
    )

    assert _ids(candidates) == [match.id]


def test_get_candidates_records_one_reason_per_nominating_seed(
    db_session: Session,
    plain_manga: Callable[[str], Manga],
) -> None:
    first_seed = plain_manga("First Seed")
    second_seed = plain_manga("Second Seed")
    shared = plain_manga("Shared")
    _recommend(db_session, first_seed, (shared, 1.0))
    _recommend(db_session, second_seed, (shared, 1.0))

    (candidate,) = CommunityCandidateSource().get_candidates(
        db_session, _query(first_seed.id, second_seed.id), 10
    )

    assert candidate.manga_id == shared.id
    assert [(r.source, r.seed_id) for r in candidate.reasons] == [
        ("community", first_seed.id),
        ("community", second_seed.id),
    ]


def test_get_candidates_skips_a_seed_without_recommendations(
    db_session: Session,
    plain_manga: Callable[[str], Manga],
) -> None:
    seed = plain_manga("Seed")
    lonely_seed = plain_manga("Lonely Seed")
    match = plain_manga("Match")
    _recommend(db_session, seed, (match, 1.0))

    candidates = CommunityCandidateSource().get_candidates(
        db_session, _query(lonely_seed.id, seed.id), 10
    )

    assert _ids(candidates) == [match.id]


def test_get_candidates_returns_at_most_k(
    db_session: Session,
    plain_manga: Callable[[str], Manga],
) -> None:
    seed = plain_manga("Seed")
    matches = [plain_manga(f"Match {i}") for i in range(5)]
    _recommend(db_session, seed, *((m, 1.0 - i / 10) for i, m in enumerate(matches)))

    candidates = CommunityCandidateSource().get_candidates(
        db_session, _query(seed.id), 2
    )

    assert _ids(candidates) == [matches[0].id, matches[1].id]
