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
    db_source = Source(
        name=name,
        weight=weight,
    )
    db.add(db_source)
    db.flush()
    return db_source


def get_source_by_name(db: Session, name: str) -> Source | None:
    return db.scalar(select(Source).where(Source.name == name))


def get_or_create_source(
    db: Session,
    *,
    name: str,
    weight: float = 1.0,
) -> Source:
    source = get_source_by_name(db, name)
    if source:
        return source
    return create_source(
        db,
        name=name,
        weight=weight,
    )


def get_source_id_by_name(db: Session, name: str) -> uuid.UUID | None:
    source = get_source_by_name(db, name)
    return source.id if source else None


def delete_source(db: Session, source: Source) -> None:
    db.delete(source)
    db.flush()
