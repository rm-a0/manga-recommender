"""Persist extracted manga records to the database."""

import uuid
from collections.abc import Sequence

import structlog
from sqlalchemy.orm import Session

from manga_recommender.db.repositories.authors import bulk_get_or_create_authors
from manga_recommender.db.repositories.manga import (
    MangaUpsertValues,
    TagLinkValues,
    bulk_add_authors_to_manga,
    bulk_add_tags_to_manga,
    bulk_update_or_create_manga,
)
from manga_recommender.db.repositories.manga_external_rating import (
    RatingUpsertValues,
    bulk_update_or_create_external_ratings,
)
from manga_recommender.db.repositories.tags import (
    TagUpsertValues,
    bulk_get_or_create_tags,
)
from manga_recommender.db.session import session_scope
from manga_recommender.ingestion.base import NormalizedMangaRecord, NormalizedTag

logger = structlog.get_logger(__name__)


def _sync_tags_for_manga(
    db: Session,
    tag_cache: dict[str, uuid.UUID],
    manga_to_tags: dict[uuid.UUID, Sequence[NormalizedTag]],
) -> None:
    """Resolve tags to ids and bulk-attach them to their manga.

    A cache miss triggers one bulk lookup-or-create query for all misses.
    """
    uncached = [
        tag
        for linked_tags in manga_to_tags.values()
        for tag in linked_tags
        if tag.name not in tag_cache
    ]
    if uncached:
        # A cached name skips the upsert, so a tag keeps the category it was
        # first seen with. AniList sends some names as both a genre and a tag,
        # so which category sticks depends on which media comes first.
        values = [TagUpsertValues(name=t.name, category=t.category) for t in uncached]
        tag_cache.update(bulk_get_or_create_tags(db, values))

    # A tag can resolve to no id, when its name normalizes to an empty key.
    # Such a tag has nothing to link.
    link_values = [
        TagLinkValues(
            manga_id=manga_id,
            tag_id=tag_cache[tag.name],
            rank=tag.rank,
            is_spoiler=tag.is_spoiler,
        )
        for manga_id, tags in manga_to_tags.items()
        for tag in tags
        if tag.name in tag_cache
    ]
    bulk_add_tags_to_manga(db, link_values)


def _sync_authors_for_manga(
    db: Session,
    author_cache: dict[str, uuid.UUID],
    manga_to_authors: dict[uuid.UUID, Sequence[str]],
) -> None:
    """Resolve authors to ids and bulk-attach them to their manga.

    A cache miss triggers one bulk lookup-or-create query for all misses.
    """
    uncached = [
        name
        for linked_names in manga_to_authors.values()
        for name in linked_names
        if name not in author_cache
    ]
    if uncached:
        author_cache.update(bulk_get_or_create_authors(db, uncached))
    # A name can resolve to no id, when its spelling normalizes to an empty
    # key. Such a name has nothing to link.
    pairs = [
        (manga_id, author_cache[name])
        for manga_id, linked_names in manga_to_authors.items()
        for name in linked_names
        if name in author_cache
    ]
    bulk_add_authors_to_manga(db, pairs)


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


def _map_manga_to_tags(
    records: Sequence[NormalizedMangaRecord],
    external_id_to_manga_id: dict[str, uuid.UUID],
) -> dict[uuid.UUID, Sequence[NormalizedTag]]:
    """Map each manga id to its tags.

    Skips records with no tags instead of mapping them to an empty list.
    """
    return {external_id_to_manga_id[r.external_id]: r.tags for r in records if r.tags}


def load_batch(
    records: Sequence[NormalizedMangaRecord],
    source_id: uuid.UUID,
    tag_cache: dict[str, uuid.UUID],
    author_cache: dict[str, uuid.UUID],
) -> None:
    """Persist a batch of normalized manga records to the database in one transaction.

    Manga, tag, author, and rating writes are all bulk-upserted.
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
                    image_url=r.image_url,
                    status=r.status,
                    external_id=r.external_id,
                    votes_count=r.votes_count,
                )
                for r in records
            ],
        )
        # A record the manga upsert could not map has no id for its tags,
        # authors, or rating. Drop it instead of failing the whole batch.
        mapped = [r for r in records if r.external_id in external_id_to_manga_id]
        if len(mapped) != len(records):
            logger.warning(
                "records_unmapped",
                dropped=len(records) - len(mapped),
                total=len(records),
            )

        manga_to_tags = _map_manga_to_tags(mapped, external_id_to_manga_id)
        _sync_tags_for_manga(session, tag_cache, manga_to_tags)

        manga_to_authors = _map_manga_to_authors(mapped, external_id_to_manga_id)
        _sync_authors_for_manga(session, author_cache, manga_to_authors)

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
