import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from manga_recommender.db.models.genres import Genre
from manga_recommender.db.models.manga import Manga, MangaStatus
from manga_recommender.db.models.manga_external_ratings import MangaExternalRating


def create_manga(
    db: Session,
    *,
    mal_id: int | None = None,
    title: str,
    author: str,
    published_date: datetime | None = None,
    status: MangaStatus | None = None,
) -> Manga:
    db_manga = Manga(
        mal_id=mal_id,
        title=title,
        author=author,
        published_date=published_date,
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
    status: MangaStatus | None = None,
) -> Manga:
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
    status: MangaStatus | None = None,
) -> Manga:
    updates = {
        "mal_id": mal_id,
        "title": title,
        "author": author,
        "published_date": published_date,
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
    status: MangaStatus | None = None,
) -> Manga:
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
            status=status,
        )
    return create_manga(
        db,
        mal_id=mal_id,
        title=title,
        author=author,
        published_date=published_date,
        status=status,
    )


def delete_manga(db: Session, manga: Manga) -> None:
    db.delete(manga)
    db.flush()


def get_manga_by_mal_id(db: Session, mal_id: int) -> Manga | None:
    return db.scalar(select(Manga).where(Manga.mal_id == mal_id))


def get_manga_by_source_external_id(
    db: Session,
    source_id: uuid.UUID,
    external_id: str,
) -> Manga | None:
    return db.scalar(
        select(Manga)
        .join(MangaExternalRating)
        .where(
            MangaExternalRating.source_id == source_id,
            MangaExternalRating.external_id == external_id,
        )
    )


def assign_genres_to_manga(db: Session, manga: Manga, genres: list[Genre]) -> Manga:
    manga.genres = genres
    db.flush()
    return manga


def add_genres_to_manga(db: Session, manga: Manga, genres: list[Genre]) -> Manga:
    for genre in genres:
        if genre not in manga.genres:
            manga.genres.append(genre)
    db.flush()
    return manga
