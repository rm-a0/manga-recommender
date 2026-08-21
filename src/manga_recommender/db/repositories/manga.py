"""Data-access functions for the Manga model."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from manga_recommender.db.models.genres import Genre
from manga_recommender.db.models.manga import Manga, MangaStatus
from manga_recommender.db.models.manga_external_ratings import MangaExternalRating
from manga_recommender.ingestion.base import NormalizedMangaRecord


def create_manga(
    db: Session,
    *,
    mal_id: int | None = None,
    title: str,
    author: str,
    published_date: datetime | None = None,
    description: str | None = None,
    status: MangaStatus | None = None,
) -> Manga:
    """Create and persist a new manga."""
    db_manga = Manga(
        mal_id=mal_id,
        title=title,
        author=author,
        published_date=published_date,
        description=description,
        status=status,
    )
    db.add(db_manga)
    db.flush()
    return db_manga


def get_or_create_manga(
    db: Session,
    *,
    mal_id: int | None = None,
    source_id: uuid.UUID | None = None,
    external_id: str | None = None,
    title: str,
    author: str,
    published_date: datetime | None = None,
    description: str | None = None,
    status: MangaStatus | None = None,
) -> Manga:
    """Return the matching manga, creating it if none exists.

    Looks up by mal_id first, falling back to source_id and external_id.
    """
    manga = None
    if mal_id is not None:
        manga = get_manga_by_mal_id(db, mal_id)
    elif source_id is not None and external_id is not None:
        manga = get_manga_by_source_external_id(db, source_id, external_id)
    if manga:
        return manga
    return create_manga(
        db,
        mal_id=mal_id,
        title=title,
        author=author,
        published_date=published_date,
        description=description,
        status=status,
    )


def update_manga(
    db: Session,
    manga: Manga,
    *,
    mal_id: int | None = None,
    title: str | None = None,
    author: str | None = None,
    published_date: datetime | None = None,
    description: str | None = None,
    status: MangaStatus | None = None,
) -> Manga:
    """Update the given manga's fields and persist the changes.

    Only fields with a non-None value are updated.
    """
    updates = {
        "mal_id": mal_id,
        "title": title,
        "author": author,
        "published_date": published_date,
        "description": description,
        "status": status,
    }
    for attr, value in updates.items():
        if value is not None:
            setattr(manga, attr, value)
    db.flush()
    return manga


def update_or_create_manga(
    db: Session,
    *,
    mal_id: int | None = None,
    source_id: uuid.UUID | None = None,
    external_id: str | None = None,
    title: str,
    author: str,
    published_date: datetime | None = None,
    description: str | None = None,
    status: MangaStatus | None = None,
) -> Manga:
    """Update the matching manga if one exists, otherwise create it.

    Uses the same mal_id/source_id lookup order as get_or_create_manga.
    """
    manga = None
    if mal_id is not None:
        manga = get_manga_by_mal_id(db, mal_id)
    elif source_id is not None and external_id is not None:
        manga = get_manga_by_source_external_id(db, source_id, external_id)
    if manga:
        return update_manga(
            db,
            manga,
            mal_id=mal_id,
            title=title,
            author=author,
            published_date=published_date,
            description=description,
            status=status,
        )
    return create_manga(
        db,
        mal_id=mal_id,
        title=title,
        author=author,
        published_date=published_date,
        description=description,
        status=status,
    )


def delete_manga(db: Session, manga: Manga) -> None:
    """Delete the given manga."""
    db.delete(manga)
    db.flush()


def get_manga_by_mal_id(db: Session, mal_id: int) -> Manga | None:
    """Return the manga with the given MyAnimeList ID, or None if not found."""
    return db.scalar(select(Manga).where(Manga.mal_id == mal_id))


def get_manga_by_source_external_id(
    db: Session,
    source_id: uuid.UUID,
    external_id: str,
) -> Manga | None:
    """Return the manga matching a source's external ID, or None if not found."""
    return db.scalar(
        select(Manga)
        .join(MangaExternalRating)
        .where(
            MangaExternalRating.source_id == source_id,
            MangaExternalRating.external_id == external_id,
        )
    )


def assign_genres_to_manga(db: Session, manga: Manga, genres: list[Genre]) -> Manga:
    """Replace a manga's genres with the given list."""
    manga.genres = genres
    db.flush()
    return manga


def add_genres_to_manga(db: Session, manga: Manga, genres: list[Genre]) -> Manga:
    """Add genres to a manga, skipping any it already has."""
    for genre in genres:
        if genre not in manga.genres:
            manga.genres.append(genre)
    db.flush()
    return manga


def _bulk_upsert_without_mal_id(
    db: Session, records: Sequence[NormalizedMangaRecord], source_id: uuid.UUID
) -> dict[str, uuid.UUID]:
    """Bulk upsert manga records that do not have a mal_id, returning a mapping of external_id to manga_id."""
    id_map = {}
    for record in records:
        manga_id = update_or_create_manga(
            db,
            source_id=source_id,
            external_id=record.external_id,
            title=record.title,
            author=record.author,
            published_date=record.published_date,
            description=record.description,
            status=record.status,
        )
        id_map[record.external_id] = manga_id.id
    return id_map


def _bulk_upsert_with_mal_id(
    db: Session, records: Sequence[NormalizedMangaRecord]
) -> dict[str, uuid.UUID]:
    """Bulk upsert manga records that have a mal_id, returning a mapping of external_id to manga_id."""
    if not records:
        return {}
    # Extract the relevant fields from the records for bulk upsert
    values = [
        {
            "mal_id": record.mal_id,
            "title": record.title,
            "author": record.author,
            "published_date": record.published_date,
            "description": record.description,
            "status": record.status,
        }
        for record in records
    ]
    insert_stmt = pg_insert(Manga).values(values)
    stmt = insert_stmt.on_conflict_do_update(
        index_elements=[Manga.mal_id],
        set_={
            "title": func.coalesce(insert_stmt.excluded.title, Manga.title),
            "author": func.coalesce(insert_stmt.excluded.author, Manga.author),
            "published_date": func.coalesce(
                insert_stmt.excluded.published_date, Manga.published_date
            ),
            "description": func.coalesce(
                insert_stmt.excluded.description, Manga.description
            ),
            "status": func.coalesce(insert_stmt.excluded.status, Manga.status),
        },
    ).returning(Manga.mal_id, Manga.id)

    # Execute the statement and build a mapping of external_id to manga_id
    id_map = {}
    mal_id_to_external_id = {r.mal_id: r.external_id for r in records}
    for mal_id, manga_id in db.execute(stmt):
        external_id = mal_id_to_external_id.get(mal_id)
        if external_id:
            id_map[external_id] = manga_id

    return id_map


def bulk_update_or_create_manga(
    db: Session, records: Sequence[NormalizedMangaRecord], source_id: uuid.UUID
) -> dict[str, uuid.UUID]:
    """Bulk upsert manga records, returning a mapping of external_id to manga_id."""
    records_with_mal_id = [r for r in records if r.mal_id is not None]
    records_without_mal_id = [r for r in records if r.mal_id is None]

    return {
        **_bulk_upsert_with_mal_id(db, records_with_mal_id),
        **_bulk_upsert_without_mal_id(db, records_without_mal_id, source_id),
    }
