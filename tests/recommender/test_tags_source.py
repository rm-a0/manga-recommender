"""Tests for the tags candidate source."""

import uuid
from collections.abc import Callable

from sqlalchemy.orm import Session

from manga_recommender.db.models.manga import Manga
from manga_recommender.recommender.base import Candidate, RecommendationQuery
from manga_recommender.recommender.candidate_sources.tags import TagsCandidateSource


def _query(*liked: uuid.UUID, limit: int = 20) -> RecommendationQuery:
    return RecommendationQuery(
        liked_ids=liked,
        disliked_ids=(),
        source_weights={"tags": 1.0},
        limit=limit,
    )


def _ids(candidates: list[Candidate]) -> list[uuid.UUID]:
    return [candidate.manga_id for candidate in candidates]


def test_get_candidates_returns_manga_ids(
    db_session: Session,
    plain_manga: Callable[[str], Manga],
    tag_manga: Callable[[uuid.UUID, str], None],
) -> None:
    seed = plain_manga("Seed")
    tag_manga(seed.id, "Action")
    match = plain_manga("Match")
    tag_manga(match.id, "Action")

    candidates = TagsCandidateSource().get_candidates(db_session, _query(seed.id), 10)

    assert _ids(candidates) == [match.id]


def test_get_candidates_ranks_the_manga_with_more_shared_tags_first(
    db_session: Session,
    plain_manga: Callable[[str], Manga],
    tag_manga: Callable[[uuid.UUID, str], None],
) -> None:
    seed = plain_manga("Seed")
    tag_manga(seed.id, "Action")
    tag_manga(seed.id, "Drama")
    one_shared = plain_manga("One Shared")
    tag_manga(one_shared.id, "Action")
    two_shared = plain_manga("Two Shared")
    tag_manga(two_shared.id, "Action")
    tag_manga(two_shared.id, "Drama")

    candidates = TagsCandidateSource().get_candidates(db_session, _query(seed.id), 10)

    assert _ids(candidates) == [two_shared.id, one_shared.id]


def test_get_candidates_skips_a_seed_without_tags(
    db_session: Session,
    plain_manga: Callable[[str], Manga],
    tag_manga: Callable[[uuid.UUID, str], None],
) -> None:
    untagged_seed = plain_manga("Untagged Seed")
    tagged_seed = plain_manga("Tagged Seed")
    tag_manga(tagged_seed.id, "Action")
    match = plain_manga("Match")
    tag_manga(match.id, "Action")

    candidates = TagsCandidateSource().get_candidates(
        db_session, _query(untagged_seed.id, tagged_seed.id), 10
    )

    assert _ids(candidates) == [match.id]


def test_get_candidates_records_one_reason_per_nominating_seed(
    db_session: Session,
    plain_manga: Callable[[str], Manga],
    tag_manga: Callable[[uuid.UUID, str], None],
) -> None:
    first_seed = plain_manga("First Seed")
    tag_manga(first_seed.id, "Action")
    second_seed = plain_manga("Second Seed")
    tag_manga(second_seed.id, "Drama")
    shared_match = plain_manga("Shared Match")
    tag_manga(shared_match.id, "Action")
    tag_manga(shared_match.id, "Drama")

    candidates = TagsCandidateSource().get_candidates(
        db_session, _query(first_seed.id, second_seed.id), 10
    )

    shared = next(c for c in candidates if c.manga_id == shared_match.id)
    assert {reason.seed_id for reason in shared.reasons} == {
        first_seed.id,
        second_seed.id,
    }
    assert {reason.source for reason in shared.reasons} == {"tags"}


def test_get_candidates_returns_nothing_without_seeds(db_session: Session) -> None:
    assert TagsCandidateSource().get_candidates(db_session, _query(), 10) == []
