"""Data-access functions for the Source model."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from manga_recommender.db.models.sources import Source


def create_source(
    db: Session,
    *,
    name: str,
    weight: float = 1.0,
) -> Source:
    """Create and persist a new source."""
    db_source = Source(
        name=name,
        weight=weight,
    )
    db.add(db_source)
    db.flush()
    return db_source


def get_source_by_name(db: Session, name: str) -> Source | None:
    """Return the source with the given name, or None if not found."""
    return db.scalar(select(Source).where(Source.name == name))


def get_or_create_source(
    db: Session,
    *,
    name: str,
    weight: float = 1.0,
) -> Source:
    """Return the existing source with the given name, creating it if needed."""
    source = get_source_by_name(db, name)
    return source or create_source(db, name=name, weight=weight)


def get_source_id_by_name(db: Session, name: str) -> uuid.UUID | None:
    """Return the ID of the source with the given name, or None if not found."""
    source = get_source_by_name(db, name)
    return source.id if source else None


def delete_source(db: Session, source: Source) -> None:
    """Delete the given source."""
    db.delete(source)
    db.flush()
