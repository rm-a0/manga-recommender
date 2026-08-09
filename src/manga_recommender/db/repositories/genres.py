from sqlalchemy import select
from sqlalchemy.orm import Session

from manga_recommender.db.models.genres import Genre


def create_genre(
    db: Session,
    *,
    name: str,
) -> Genre:
    db_genre = Genre(
        name=name,
    )
    db.add(db_genre)
    db.flush()
    return db_genre


def get_genre_by_name(db: Session, name: str) -> Genre | None:
    return db.scalar(select(Genre).where(Genre.name == name))


def get_or_create_genre(
    db: Session,
    *,
    name: str,
) -> Genre:
    genre = get_genre_by_name(db, name)
    if genre:
        return genre
    return create_genre(db, name=name)
