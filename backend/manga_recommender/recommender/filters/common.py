"""Helpers that the filters share. These are not filters themselves."""

import uuid
from collections.abc import Sequence, Set

from manga_recommender.recommender.base import Candidate


def drop_ids(
    candidates: Sequence[Candidate],
    excluded_manga_ids: Set[uuid.UUID],
) -> list[Candidate]:
    """Return the candidates that the given ids do not name."""
    return [c for c in candidates if c.manga_id not in excluded_manga_ids]
