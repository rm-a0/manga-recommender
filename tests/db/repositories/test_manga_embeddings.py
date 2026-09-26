"""Tests for the nearest-neighbour queries over `manga_embeddings`."""

from collections.abc import Callable

from sqlalchemy import text
from sqlalchemy.orm import Session

from manga_recommender.db.models.manga import Manga
from manga_recommender.db.repositories.manga import MangaFilters
from manga_recommender.db.repositories.manga_embeddings import (
    get_embedding_by_manga_id,
    get_manga_ids_near,
    get_nearest_neighbours,
)


def test_get_embedding_by_manga_id_returns_none_without_embedding(
    db_session: Session,
    plain_manga: Callable[[str], Manga],
) -> None:
    manga = plain_manga("No Vector")

    assert get_embedding_by_manga_id(db_session, manga.id) is None


def test_get_nearest_neighbours_orders_by_distance(
    db_session: Session,
    embedded_manga: Callable[[str, float], Manga],
) -> None:
    seed = embedded_manga("Seed", 0)
    near = embedded_manga("Near", 5)
    far = embedded_manga("Far", 60)
    opposite = embedded_manga("Opposite", 170)

    embedding = get_embedding_by_manga_id(db_session, seed.id)
    assert embedding is not None

    assert list(get_nearest_neighbours(db_session, embedding, MangaFilters(), 3)) == [
        near.id,
        far.id,
        opposite.id,
    ]


def test_get_nearest_neighbours_excludes_the_seed(
    db_session: Session,
    embedded_manga: Callable[[str, float], Manga],
) -> None:
    seed = embedded_manga("Seed", 0)
    embedded_manga("Near", 5)

    embedding = get_embedding_by_manga_id(db_session, seed.id)
    assert embedding is not None

    assert seed.id not in get_nearest_neighbours(
        db_session, embedding, MangaFilters(), 10
    )


def test_get_nearest_neighbours_returns_at_most_n(
    db_session: Session,
    embedded_manga: Callable[[str, float], Manga],
) -> None:
    seed = embedded_manga("Seed", 0)
    for degrees in (5, 10, 15, 20):
        embedded_manga(f"Match {degrees}", degrees)

    embedding = get_embedding_by_manga_id(db_session, seed.id)
    assert embedding is not None

    assert len(get_nearest_neighbours(db_session, embedding, MangaFilters(), 2)) == 2


def test_get_nearest_neighbours_returns_only_the_manga_that_pass_the_filters(
    db_session: Session,
    embedded_manga: Callable[[str, float], Manga],
) -> None:
    seed = embedded_manga("Seed", 0)
    excluded = embedded_manga("Excluded", 5)
    kept = embedded_manga("Kept", 10)

    embedding = get_embedding_by_manga_id(db_session, seed.id)
    assert embedding is not None

    found = get_nearest_neighbours(
        db_session, embedding, MangaFilters(exclude_ids=(excluded.id,)), 10
    )

    assert list(found) == [kept.id]


def test_get_nearest_neighbours_fills_n_past_a_filter_that_drops_the_nearest(
    db_session: Session,
    embedded_manga: Callable[[str, float], Manga],
) -> None:
    """More filtered-out manga sit nearer than one HNSW pass of 40 rows reaches.

    Turning off sequential scans forces the HNSW index, as on the full
    catalogue. Without the iterative scan the result is empty.
    """
    db_session.execute(text("SET LOCAL enable_seqscan = off"))
    seed = embedded_manga("Seed", 0)
    near_ids = tuple(embedded_manga(f"Near {i}", 1 + i / 10).id for i in range(60))
    first_far = embedded_manga("First Far", 80)
    second_far = embedded_manga("Second Far", 85)

    embedding = get_embedding_by_manga_id(db_session, seed.id)
    assert embedding is not None

    found = get_nearest_neighbours(
        db_session, embedding, MangaFilters(exclude_ids=near_ids), 2
    )

    assert list(found) == [first_far.id, second_far.id]


def test_get_manga_ids_near_returns_only_the_given_ids(
    db_session: Session,
    embedded_manga: Callable[[str, float], Manga],
) -> None:
    seed = embedded_manga("Seed", 0)
    asked_for = embedded_manga("Asked For", 5)
    not_asked_for = embedded_manga("Not Asked For", 6)

    embedding = get_embedding_by_manga_id(db_session, seed.id)
    assert embedding is not None

    near_ids = get_manga_ids_near(db_session, embedding, [asked_for.id], 0.9)

    assert list(near_ids) == [asked_for.id]
    assert not_asked_for.id not in near_ids


def test_get_manga_ids_near_drops_the_manga_below_the_similarity(
    db_session: Session,
    embedded_manga: Callable[[str, float], Manga],
) -> None:
    seed = embedded_manga("Seed", 0)
    twin = embedded_manga("Twin", 5)
    relative = embedded_manga("Relative", 40)

    embedding = get_embedding_by_manga_id(db_session, seed.id)
    assert embedding is not None

    # cos(5) is about 0.996 and cos(40) about 0.766, so only the twin reaches
    # a similarity of 0.9.
    near_ids = get_manga_ids_near(db_session, embedding, [twin.id, relative.id], 0.9)

    assert list(near_ids) == [twin.id]


def test_get_manga_ids_near_returns_nothing_without_ids(
    db_session: Session,
    embedded_manga: Callable[[str, float], Manga],
) -> None:
    seed = embedded_manga("Seed", 0)

    embedding = get_embedding_by_manga_id(db_session, seed.id)
    assert embedding is not None

    assert get_manga_ids_near(db_session, embedding, [], 0.9) == []
