from manga_recommender.db.repositories.manga import update_or_create_manga
from manga_recommender.db.session import session_scope
from manga_recommender.ingestion.base import NormalizedMangaRecord


def load_batch(records: list[NormalizedMangaRecord], source_name: str) -> None:
    with session_scope() as session:
        for record in records:
            manga = update_or_create_manga(
                session,
                mal_id=record.mal_id,
                source_id=None,  # TODO: get_source_id_by_name(session, source_name),
                external_id=record.external_id,
                title=record.title,
                author=record.author,
                published_date=record.published_date,
                status=record.status,
            )
            # TODO: sync genres
            # TODO: update_or_create_external_rating()
