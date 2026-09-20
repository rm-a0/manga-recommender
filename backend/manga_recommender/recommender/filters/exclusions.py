"""Drop the candidates that the reader excluded, by id or by tag."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from manga_recommender.db.repositories.manga import get_manga_ids_with_any_tags
from manga_recommender.recommender.base import Candidate, RecommendationQuery
from manga_recommender.recommender.filters.common import drop_ids


def exclude_manga_ids(
    db: Session,
    query: RecommendationQuery,
    candidates: Sequence[Candidate],
) -> list[Candidate]:
    """Return the candidates that `query.exclude_ids` does not name.

    Takes `db` to match the `Filter` type, but reads no table.
    """
    return drop_ids(candidates, query.exclude_ids)


def exclude_manga_with_tags(
    db: Session,
    query: RecommendationQuery,
    candidates: Sequence[Candidate],
) -> list[Candidate]:
    """Return the candidates that carry none of `query.excluded_tags`."""
    exclude_ids = get_manga_ids_with_any_tags(
        db,
        [candidate.manga_id for candidate in candidates],
        query.excluded_tags,
    )
    return drop_ids(candidates, set(exclude_ids))
