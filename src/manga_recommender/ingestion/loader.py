from sqlalchemy.orm import Session

from manga_recommender.db.models.manga import Manga
from manga_recommender.db.repositories.genres import get_or_create_genre
from manga_recommender.db.repositories.manga import (
    add_genres_to_manga,
    update_or_create_manga,
)
from manga_recommender.db.repositories.sources import get_source_id_by_name
from manga_recommender.db.session import session_scope
from manga_recommender.ingestion.base import NormalizedMangaRecord


def sync_genres_for_manga(
    db: Session,
    db_manga: Manga,
    genre_names: list[str],
) -> None:
    genres = [
        get_or_create_genre(db, name=genre_name.strip().casefold())
        for genre_name in genre_names
    ]
    add_genres_to_manga(db, db_manga, genres)


def load_batch(records: list[NormalizedMangaRecord], source_name: str) -> None:
    with session_scope() as session:
        for record in records:
            manga = update_or_create_manga(
                session,
                mal_id=record.mal_id,
                source_id=get_source_id_by_name(session, source_name),
                external_id=record.external_id,
                title=record.title,
                author=record.author,
                published_date=record.published_date,
                status=record.status,
            )
            if record.genres:
                sync_genres_for_manga(session, manga, record.genres)
            # TODO: update_or_create_external_rating()
