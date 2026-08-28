"""Persist extracted manga records to the database."""

import uuid
from collections.abc import Callable, Iterable, Sequence

import structlog
from sqlalchemy.orm import Session

from manga_recommender.db.repositories.authors import bulk_get_or_create_authors
from manga_recommender.db.repositories.genres import bulk_get_or_create_genres
from manga_recommender.db.repositories.manga import (
    MangaUpsertValues,
    bulk_add_authors_to_manga,
    bulk_add_genres_to_manga,
    bulk_update_or_create_manga,
)
from manga_recommender.db.repositories.manga_external_rating import (
    RatingUpsertValues,
    bulk_update_or_create_external_ratings,
)
from manga_recommender.db.session import session_scope
from manga_recommender.ingestion.base import NormalizedMangaRecord

logger = structlog.get_logger(__name__)

NameResolver = Callable[[Session, Sequence[str]], dict[str, uuid.UUID]]
LinkWriter = Callable[[Session, Sequence[tuple[uuid.UUID, uuid.UUID]]], None]


def _sync_links_for_manga(
    db: Session,
    cache: dict[str, uuid.UUID],
    names: Iterable[str],
    manga_to_names: dict[uuid.UUID, Sequence[str]],
    resolve_names: NameResolver,
    write_links: LinkWriter,
) -> None:
    """Resolve names to ids and bulk-attach them to their manga.

    A cache miss triggers one bulk lookup-or-create query for all misses.
    """
    uncached = [n for n in names if n not in cache]
    if uncached:
        cache.update(resolve_names(db, uncached))
    # A name that resolves to nothing (an author whose spelling normalizes to
    # an empty key) has no id to link.
    pairs = [
        (manga_id, cache[name])
        for manga_id, linked_names in manga_to_names.items()
        for name in linked_names
        if name in cache
    ]
    write_links(db, pairs)


def _map_manga_to_genres(
    records: Sequence[NormalizedMangaRecord],
    external_id_to_manga_id: dict[str, uuid.UUID],
) -> dict[uuid.UUID, Sequence[str]]:
    """Map each manga id to its lowercased genre names.

    Skips records with no genres instead of mapping them to an empty list.
    """
    return {
        external_id_to_manga_id[r.external_id]: [g.lower() for g in r.genres]
        for r in records
        if r.genres
    }


def _map_manga_to_authors(
    records: Sequence[NormalizedMangaRecord],
    external_id_to_manga_id: dict[str, uuid.UUID],
) -> dict[uuid.UUID, Sequence[str]]:
    """Map each manga id to its author names.

    Skips records with no authors instead of mapping them to an empty list.
    """
    return {
        external_id_to_manga_id[r.external_id]: r.authors for r in records if r.authors
    }


def load_batch(
    records: Sequence[NormalizedMangaRecord],
    source_id: uuid.UUID,
    genre_cache: dict[str, uuid.UUID],
    author_cache: dict[str, uuid.UUID],
) -> None:
    """Persist a batch of normalized manga records to the database in one transaction.

    Manga, genre, author, and rating writes are all bulk-upserted.
    """
    with session_scope() as session:
        external_id_to_manga_id = bulk_update_or_create_manga(
            session,
            source_id,
            records=[
                MangaUpsertValues(
                    mal_id=r.mal_id,
                    title=r.title,
                    published_date=r.published_date,
                    description=r.description,
                    status=r.status,
                    external_id=r.external_id,
                    votes_count=r.votes_count,
                )
                for r in records
            ],
        )
        # A record the manga upsert could not map has no id to hang its genres,
        # authors, or rating on. Drop it instead of failing the whole batch.
        mapped = [r for r in records if r.external_id in external_id_to_manga_id]
        if len(mapped) != len(records):
            logger.warning(
                "records_unmapped",
                dropped=len(records) - len(mapped),
                total=len(records),
            )

        manga_to_genres = _map_manga_to_genres(mapped, external_id_to_manga_id)
        _sync_links_for_manga(
            session,
            genre_cache,
            {g for genres in manga_to_genres.values() for g in genres},
            manga_to_genres,
            bulk_get_or_create_genres,
            bulk_add_genres_to_manga,
        )

        manga_to_authors = _map_manga_to_authors(mapped, external_id_to_manga_id)
        _sync_links_for_manga(
            session,
            author_cache,
            {a for authors in manga_to_authors.values() for a in authors},
            manga_to_authors,
            bulk_get_or_create_authors,
            bulk_add_authors_to_manga,
        )

        bulk_update_or_create_external_ratings(
            session,
            values=[
                RatingUpsertValues(
                    manga_id=external_id_to_manga_id[r.external_id],
                    source_id=source_id,
                    external_id=r.external_id,
                    raw_scale_max=r.raw_scale_max,
                    votes_count=r.votes_count,
                    fetched_at=r.fetched_at,
                    raw_score=r.raw_score,
                    score_distribution=r.score_distribution,
                )
                for r in mapped
            ],
        )
