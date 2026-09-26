"""Tests for the nearest-neighbour queries over `manga_embeddings`."""

from collections.abc import Callable

from sqlalchemy.orm import Session

from manga_recommender.db.models.manga import Manga
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

    assert list(get_nearest_neighbours(db_session, embedding, 3)) == [
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

    assert seed.id not in get_nearest_neighbours(db_session, embedding, 10)


def test_get_nearest_neighbours_returns_at_most_n(
    db_session: Session,
    embedded_manga: Callable[[str, float], Manga],
) -> None:
    seed = embedded_manga("Seed", 0)
    for degrees in (5, 10, 15, 20):
        embedded_manga(f"Match {degrees}", degrees)

    embedding = get_embedding_by_manga_id(db_session, seed.id)
    assert embedding is not None

    assert len(get_nearest_neighbours(db_session, embedding, 2)) == 2


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
