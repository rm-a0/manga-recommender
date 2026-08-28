"""Data-access functions for the Genre model."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
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


# --- Bulk operations ---


def bulk_get_or_create_genres(
    db: Session,
    names: Sequence[str],
) -> dict[str, uuid.UUID]:
    """Return a mapping of genre names to their UUIDs, creating any that don't exist."""
    # A repeated name in one INSERT raises CardinalityViolation.
    values = [{"name": n} for n in dict.fromkeys(names)]
    if not values:
        return {}
    insert_stmt = pg_insert(Genre).values(values)
    stmt = insert_stmt.on_conflict_do_update(
        index_elements=["name"],
        set_={"name": insert_stmt.excluded.name},
    ).returning(Genre.name, Genre.id)
    return {name: genre_id for name, genre_id in db.execute(stmt)}
