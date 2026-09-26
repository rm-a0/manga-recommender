"""Tests for the recommender filters."""

import uuid
from collections.abc import Callable

from sqlalchemy.orm import Session

from manga_recommender.db.models.manga import Manga
from manga_recommender.recommender.base import Candidate
from manga_recommender.recommender.filters.common import drop_ids
from manga_recommender.recommender.filters.dislikes import drop_near_dislikes
from manga_recommender.recommender.filters.exclusions import (
    exclude_manga_ids,
    exclude_manga_with_tags,
)
from tests.recommender.queries import make_query


def _candidates(*manga_ids: uuid.UUID) -> list[Candidate]:
    return [Candidate(manga_id=manga_id) for manga_id in manga_ids]


def test_drop_ids_keeps_the_candidates_that_are_not_named() -> None:
    kept, dropped = uuid.uuid4(), uuid.uuid4()

    result = drop_ids(_candidates(kept, dropped), {dropped})

    assert [c.manga_id for c in result] == [kept]


def test_exclude_manga_ids_drops_the_excluded_candidates(
    db_session: Session,
) -> None:
    kept, excluded = uuid.uuid4(), uuid.uuid4()
    query = make_query(exclude_ids=frozenset({excluded}))

    result = exclude_manga_ids(db_session, query, _candidates(kept, excluded))

    assert [c.manga_id for c in result] == [kept]


def test_exclude_manga_with_tags_drops_a_candidate_that_carries_one(
    db_session: Session,
    plain_manga: Callable[[str], Manga],
    tag_manga: Callable[[uuid.UUID, str], None],
) -> None:
    tagged = plain_manga("Tagged")
    untagged = plain_manga("Untagged")
    tag_manga(tagged.id, "Ecchi")
    tag_manga(untagged.id, "Adventure")
    query = make_query(excluded_tags=frozenset({"Ecchi"}))

    result = exclude_manga_with_tags(
        db_session, query, _candidates(tagged.id, untagged.id)
    )

    assert [c.manga_id for c in result] == [untagged.id]


def test_exclude_manga_with_tags_keeps_every_candidate_without_excluded_tags(
    db_session: Session,
    plain_manga: Callable[[str], Manga],
    tag_manga: Callable[[uuid.UUID, str], None],
) -> None:
    manga = plain_manga("Tagged")
    tag_manga(manga.id, "Ecchi")

    result = exclude_manga_with_tags(db_session, make_query(), _candidates(manga.id))

    assert [c.manga_id for c in result] == [manga.id]


def test_drop_near_dislikes_drops_a_near_duplicate(
    db_session: Session,
    embedded_manga: Callable[[str, float], Manga],
) -> None:
    disliked = embedded_manga("Disliked", 0)
    twin = embedded_manga("Twin", 5)
    unrelated = embedded_manga("Unrelated", 60)
    query = make_query(disliked_ids=(disliked.id,))

    result = drop_near_dislikes(db_session, query, _candidates(twin.id, unrelated.id))

    assert [c.manga_id for c in result] == [unrelated.id]


def test_drop_near_dislikes_uses_every_disliked_manga(
    db_session: Session,
    embedded_manga: Callable[[str, float], Manga],
) -> None:
    first_disliked = embedded_manga("First Disliked", 0)
    second_disliked = embedded_manga("Second Disliked", 90)
    first_twin = embedded_manga("First Twin", 5)
    second_twin = embedded_manga("Second Twin", 85)
    unrelated = embedded_manga("Unrelated", 45)
    query = make_query(disliked_ids=(first_disliked.id, second_disliked.id))

    result = drop_near_dislikes(
        db_session, query, _candidates(first_twin.id, second_twin.id, unrelated.id)
    )

    assert [c.manga_id for c in result] == [unrelated.id]


def test_drop_near_dislikes_reads_the_cutoff_from_the_query(
    db_session: Session,
    embedded_manga: Callable[[str, float], Manga],
) -> None:
    disliked = embedded_manga("Disliked", 0)
    # cos(30) is about 0.866: above a cutoff of 0.8, below a cutoff of 0.9.
    relative = embedded_manga("Relative", 30)
    strict = make_query(disliked_ids=(disliked.id,), dislike_similarity_cutoff=0.9)
    loose = make_query(disliked_ids=(disliked.id,), dislike_similarity_cutoff=0.8)

    kept = drop_near_dislikes(db_session, strict, _candidates(relative.id))
    dropped = drop_near_dislikes(db_session, loose, _candidates(relative.id))

    assert [c.manga_id for c in kept] == [relative.id]
    assert dropped == []


def test_drop_near_dislikes_keeps_everything_without_dislikes(
    db_session: Session,
    embedded_manga: Callable[[str, float], Manga],
) -> None:
    manga = embedded_manga("Manga", 0)

    result = drop_near_dislikes(db_session, make_query(), _candidates(manga.id))

    assert [c.manga_id for c in result] == [manga.id]


def test_drop_near_dislikes_skips_a_disliked_manga_without_an_embedding(
    db_session: Session,
    embedded_manga: Callable[[str, float], Manga],
    plain_manga: Callable[[str], Manga],
) -> None:
    bare_dislike = plain_manga("Bare Dislike")
    candidate = embedded_manga("Candidate", 0)
    query = make_query(disliked_ids=(bare_dislike.id,))

    result = drop_near_dislikes(db_session, query, _candidates(candidate.id))

    assert [c.manga_id for c in result] == [candidate.id]
