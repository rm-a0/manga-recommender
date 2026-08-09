"""Data-access functions for the Genre model."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from manga_recommender.db.models.genres import Genre


def create_genre(
    db: Session,
    *,
    name: str,
) -> Genre:
    """Create and persist a new genre."""
    db_genre = Genre(
        name=name,
    )
    db.add(db_genre)
    db.flush()
    return db_genre


def get_genre_by_name(db: Session, name: str) -> Genre | None:
    """Return the genre with the given name, or None if not found."""
    return db.scalar(select(Genre).where(Genre.name == name))


def get_or_create_genre(
    db: Session,
    *,
    name: str,
) -> Genre:
    """Return the existing genre with the given name, creating it if needed."""
    genre = get_genre_by_name(db, name)
    if genre:
        return genre
    return create_genre(db, name=name)
