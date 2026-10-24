import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from manga_recommender.db.models.manga_similarities import (
    MangaSimilarity,
    SimilarityMethod,
)
from manga_recommender.db.repositories.manga import (
    MangaFilters,
    create_manga,
    delete_manga,
)
from manga_recommender.db.repositories.manga_similarities import (
    SimilarityValues,
    bulk_create_manga_similarities,
    delete_manga_similarities_by_method,
    get_similar_manga_ids,
)


def _edge(
    manga_id: uuid.UUID,
    similar_manga_id: uuid.UUID,
    method: SimilarityMethod = SimilarityMethod.COMMUNITY_RECS,
    score: float = 0.5,
) -> SimilarityValues:
    """Build one SimilarityValues row."""
    return SimilarityValues(
        manga_id=manga_id,
        method=method,
        similar_manga_id=similar_manga_id,
        score=score,
    )


def _stored(db_session: Session) -> set[tuple[uuid.UUID, SimilarityMethod, uuid.UUID]]:
    """Reload the key of every similarity edge straight from the database."""
    db_session.expire_all()
    return {
        (row.manga_id, row.method, row.similar_manga_id)
        for row in db_session.scalars(select(MangaSimilarity))
    }


def _manga_ids(db_session: Session, count: int) -> list[uuid.UUID]:
    """Create `count` manga and return their IDs."""
    return [create_manga(db_session, title=f"Manga {i}").id for i in range(count)]


def test_bulk_create_inserts_every_edge(db_session: Session) -> None:
    a, b, c = _manga_ids(db_session, 3)

    bulk_create_manga_similarities(
        db_session,
        [_edge(a, b, score=0.75), _edge(a, c, score=0.25)],
    )

    db_session.expire_all()
    scores = {
        row.similar_manga_id: row.score
        for row in db_session.scalars(select(MangaSimilarity))
    }
    assert scores == {b: 0.75, c: 0.25}


def test_bulk_create_with_no_values_inserts_nothing(db_session: Session) -> None:
    bulk_create_manga_similarities(db_session, [])

    assert _stored(db_session) == set()


def test_delete_by_method_keeps_other_methods_and_returns_the_count(
    db_session: Session,
) -> None:
    a, b, c = _manga_ids(db_session, 3)
    bulk_create_manga_similarities(
        db_session,
        [
            _edge(a, b),
            _edge(a, c),
            _edge(a, b, method=SimilarityMethod.COLLAB),
        ],
    )

    deleted = delete_manga_similarities_by_method(
        db_session, SimilarityMethod.COMMUNITY_RECS
    )

    assert deleted == 2
    assert _stored(db_session) == {(a, SimilarityMethod.COLLAB, b)}


def test_delete_by_method_on_an_empty_table_returns_zero(db_session: Session) -> None:
    assert delete_manga_similarities_by_method(db_session, SimilarityMethod.COLLAB) == 0


def test_deleting_a_manga_deletes_its_edges_in_both_directions(
    db_session: Session,
) -> None:
    # Both foreign keys cascade, so no edge can point at a manga that is gone.
    removed = create_manga(db_session, title="Removed")
    a, b = _manga_ids(db_session, 2)
    bulk_create_manga_similarities(
        db_session,
        [_edge(removed.id, a), _edge(b, removed.id), _edge(a, b)],
    )

    delete_manga(db_session, removed)

    assert _stored(db_session) == {(a, SimilarityMethod.COMMUNITY_RECS, b)}


def test_get_similar_manga_ids_returns_the_best_score_first(
    db_session: Session,
) -> None:
    seed, weak, strong = _manga_ids(db_session, 3)
    bulk_create_manga_similarities(
        db_session, [_edge(seed, weak, score=0.25), _edge(seed, strong, score=0.75)]
    )

    assert get_similar_manga_ids(
        db_session, seed, SimilarityMethod.COMMUNITY_RECS, MangaFilters(), 10
    ) == [strong, weak]


def test_get_similar_manga_ids_breaks_a_tie_by_id(db_session: Session) -> None:
    seed, *tied = _manga_ids(db_session, 4)
    bulk_create_manga_similarities(db_session, [_edge(seed, t) for t in tied])

    assert get_similar_manga_ids(
        db_session, seed, SimilarityMethod.COMMUNITY_RECS, MangaFilters(), 10
    ) == sorted(tied)


def test_get_similar_manga_ids_filters_before_it_limits(db_session: Session) -> None:
    # The best neighbour fails the filter. With a limit of one, the next best
    # must take its place instead of an empty result.
    seed, excluded, kept = _manga_ids(db_session, 3)
    bulk_create_manga_similarities(
        db_session,
        [_edge(seed, excluded, score=0.75), _edge(seed, kept, score=0.25)],
    )

    assert get_similar_manga_ids(
        db_session,
        seed,
        SimilarityMethod.COMMUNITY_RECS,
        MangaFilters(exclude_ids=(excluded,)),
        1,
    ) == [kept]


def test_get_similar_manga_ids_reads_only_one_manga_and_method(
    db_session: Session,
) -> None:
    seed, other_seed, match, collab, unrelated = _manga_ids(db_session, 5)
    bulk_create_manga_similarities(
        db_session,
        [
            _edge(seed, match),
            _edge(seed, collab, method=SimilarityMethod.COLLAB),
            _edge(other_seed, unrelated),
        ],
    )

    assert get_similar_manga_ids(
        db_session, seed, SimilarityMethod.COMMUNITY_RECS, MangaFilters(), 10
    ) == [match]
