"""Tests that every registered candidate source honours the query filters."""

import uuid
from collections.abc import Callable

import pytest
from sqlalchemy.orm import Session

from manga_recommender.db.models.manga import Manga
from manga_recommender.db.repositories.manga import MangaFilters
from manga_recommender.recommender.registry import (
    get_candidate_source,
    get_source_names,
)
from tests.recommender.queries import make_query


@pytest.mark.parametrize("source_name", sorted(get_source_names()))
def test_every_source_returns_only_the_manga_that_pass_the_filters(
    source_name: str,
    db_session: Session,
    embedded_manga: Callable[[str, float], Manga],
    tag_manga: Callable[[uuid.UUID, str], None],
) -> None:
    """A new source must apply `query.filters` in its own query.

    Both manga match the seed for every source, so the source nominates the
    kept manga and must leave out the excluded one. A new source that needs
    other data must add it here.
    """
    seed = embedded_manga("Seed", 0)
    excluded = embedded_manga("Excluded", 5)
    kept = embedded_manga("Kept", 10)
    for manga in (seed, excluded, kept):
        tag_manga(manga.id, "Action")
    query = make_query(
        liked_ids=(seed.id,),
        source_weights={source_name: 1.0},
        filters=MangaFilters(exclude_ids=(excluded.id,)),
    )

    candidates = get_candidate_source(source_name).get_candidates(db_session, query, 10)

    assert [candidate.manga_id for candidate in candidates] == [kept.id]
