from sqlalchemy.orm import Session

from manga_recommender.db.repositories.genres import (
    create_genre,
    get_genre_by_name,
    get_or_create_genre,
)


def test_create_genre_persists_given_name(db_session: Session) -> None:
    genre = create_genre(db_session, name="action")

    assert genre.id is not None
    assert genre.name == "action"


def test_get_genre_by_name_returns_matching_genre(db_session: Session) -> None:
    created = create_genre(db_session, name="drama")

    found = get_genre_by_name(db_session, "drama")

    assert found is not None
    assert found.id == created.id


def test_get_genre_by_name_returns_none_when_missing(db_session: Session) -> None:
    assert get_genre_by_name(db_session, "no-such-genre") is None


def test_get_or_create_genre_returns_existing_genre(db_session: Session) -> None:
    created = create_genre(db_session, name="comedy")

    found = get_or_create_genre(db_session, name="comedy")

    assert found.id == created.id


def test_get_or_create_genre_creates_when_missing(db_session: Session) -> None:
    genre = get_or_create_genre(db_session, name="horror")

    assert genre.id is not None
    assert get_genre_by_name(db_session, "horror") is not None
