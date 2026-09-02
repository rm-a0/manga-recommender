"""Data-access functions for the Manga model."""

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import NamedTuple, TypedDict

from sqlalchemy import delete, exists, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, selectinload

from manga_recommender.db.models.authors import Author, manga_authors
from manga_recommender.db.models.manga import Manga, MangaStatus
from manga_recommender.db.models.manga_external_ratings import MangaExternalRating
from manga_recommender.db.models.tags import Tag, manga_tags


class MangaUpsertValues(TypedDict):
    """Column values for one bulk-upserted manga row, plus its correlation keys."""

    # Note: external_id is not a Manga column. It's the correlation key used to
    # route no-mal_id records to the fallback path and to recover external_id
    # from mal_id after the bulk RETURNING.
    external_id: str

    # Note: votes_count is not a Manga column either. It only arbitrates which
    # source entry wins when several share one mal_id. See _bulk_upsert_with_mal_id.
    votes_count: int | None

    mal_id: int | None
    title: str
    published_date: datetime | None
    description: str | None
    status: MangaStatus | None
    image_url: str | None


class TagLinkValues(TypedDict):
    """Column values for one bulk-upserted manga-tag link."""

    manga_id: uuid.UUID
    tag_id: uuid.UUID
    rank: int | None
    is_spoiler: bool


class TagLink(NamedTuple):
    """One manga-tag link: the tag, plus the attributes of the link itself."""

    tag: Tag
    rank: int | None
    is_spoiler: bool


def get_manga_tag_links(db: Session, manga_id: uuid.UUID) -> Sequence[TagLink]:
    """Return the tag links for one manga, highest rank first.

    A link with no rank sorts last. A NULL rank means the source asserts the
    tag but gives it no weight.
    """
    stmt = (
        select(Tag, manga_tags.c.rank, manga_tags.c.is_spoiler)
        .join(manga_tags, Tag.id == manga_tags.c.tag_id)
        .where(manga_tags.c.manga_id == manga_id)
        .order_by(manga_tags.c.rank.desc().nullslast())
    )
    return [TagLink(tag=t, rank=r, is_spoiler=s) for t, r, s in db.execute(stmt)]


def get_manga_by_id(
    db: Session,
    manga_id: uuid.UUID,
) -> Manga | None:
    """Return the manga with the given ID, or None if not found.

    Loads authors. Tags come from get_manga_tag_links, which also reads the
    rank and spoiler flag off the link row.
    """
    return db.scalar(
        select(Manga).where(Manga.id == manga_id).options(selectinload(Manga.authors))
    )


def get_all_manga(
    db: Session,
    *,
    limit: int,
    offset: int,
) -> Sequence[Manga]:
    """Return one page of manga, ordered by title.

    Loads authors, because the list response needs the author names.
    """
    return db.scalars(
        select(Manga)
        .order_by(Manga.title, Manga.id)
        .offset(offset)
        .limit(limit)
        .options(selectinload(Manga.authors))
    ).all()


def count_manga(db: Session) -> int:
    """Return the number of manga rows."""
    count = db.scalar(select(func.count()).select_from(Manga))
    if not count:
        return 0
    return count


def create_manga(
    db: Session,
    *,
    mal_id: int | None = None,
    title: str,
    published_date: datetime | None = None,
    description: str | None = None,
    image_url: str | None = None,
    status: MangaStatus | None = None,
) -> Manga:
    """Create and persist a new manga."""
    db_manga = Manga(
        mal_id=mal_id,
        title=title,
        published_date=published_date,
        description=description,
        image_url=image_url,
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
    published_date: datetime | None = None,
    description: str | None = None,
    image_url: str | None = None,
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
        published_date=published_date,
        description=description,
        image_url=image_url,
        status=status,
    )


def update_manga(
    db: Session,
    manga: Manga,
    *,
    mal_id: int | None = None,
    title: str | None = None,
    published_date: datetime | None = None,
    description: str | None = None,
    image_url: str | None = None,
    status: MangaStatus | None = None,
) -> Manga:
    """Update the given manga's fields and persist the changes.

    Only fields with a non-None value are updated.
    """
    updates = {
        "mal_id": mal_id,
        "title": title,
        "published_date": published_date,
        "description": description,
        "image_url": image_url,
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
    published_date: datetime | None = None,
    description: str | None = None,
    image_url: str | None = None,
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
            published_date=published_date,
            description=description,
            image_url=image_url,
            status=status,
        )
    return create_manga(
        db,
        mal_id=mal_id,
        title=title,
        published_date=published_date,
        description=description,
        image_url=image_url,
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
        .join(Manga.external_ratings)
        .where(
            MangaExternalRating.source_id == source_id,
            MangaExternalRating.external_id == external_id,
        )
    )


def assign_authors_to_manga(db: Session, manga: Manga, authors: list[Author]) -> Manga:
    """Replace a manga's authors with the given list."""
    manga.authors = authors
    db.flush()
    return manga


def add_authors_to_manga(db: Session, manga: Manga, authors: list[Author]) -> Manga:
    """Add authors to a manga, skipping any it already has."""
    for author in authors:
        if author not in manga.authors:
            manga.authors.append(author)
    db.flush()
    return manga


# --- Bulk operations ---


def _bulk_upsert_without_mal_id(
    db: Session,
    records: Sequence[MangaUpsertValues],
    source_id: uuid.UUID,
) -> dict[str, uuid.UUID]:
    """Upsert manga records that lack a mal_id, one at a time.

    Falls back to the source_id/external_id match. A NULL mal_id never
    conflicts with another NULL, so these rows can't go through the
    mal_id-keyed bulk path.
    """
    id_map = {}
    for record in records:
        manga_id = update_or_create_manga(
            db,
            source_id=source_id,
            external_id=record["external_id"],
            title=record["title"],
            published_date=record["published_date"],
            description=record["description"],
            image_url=record["image_url"],
            status=record["status"],
        )
        id_map[record["external_id"]] = manga_id.id
    return id_map


def _vote_count(record: MangaUpsertValues) -> int:
    """Return a record's vote count, sorting a missing count below zero votes."""
    votes = record["votes_count"]
    return -1 if votes is None else votes


def _pick_canonical_by_votes(
    records: Sequence[MangaUpsertValues],
) -> list[MangaUpsertValues]:
    """Keep one record per mal_id: the one with the most votes.

    Several source entries can share a mal_id. A SQL insert needs one row per
    key. The vote count decides which entry's metadata to keep.
    """
    winners: dict[int, MangaUpsertValues] = {}
    for record in records:
        mal_id = record["mal_id"]
        if mal_id is None:
            continue
        incumbent = winners.get(mal_id)
        if incumbent is None or _vote_count(record) > _vote_count(incumbent):
            winners[mal_id] = record
    return list(winners.values())


def _bulk_upsert_with_mal_id(
    db: Session,
    records: Sequence[MangaUpsertValues],
) -> dict[str, uuid.UUID]:
    """Bulk-upsert manga records that have a mal_id in one round trip."""
    if not records:
        return {}
    values = [
        {
            "mal_id": record["mal_id"],
            "title": record["title"],
            "published_date": record["published_date"],
            "description": record["description"],
            "image_url": record["image_url"],
            "status": record["status"],
        }
        for record in _pick_canonical_by_votes(records)
    ]
    insert_stmt = pg_insert(Manga).values(values)
    stmt = insert_stmt.on_conflict_do_update(
        index_elements=[Manga.mal_id],
        set_={
            "title": func.coalesce(insert_stmt.excluded.title, Manga.title),
            "published_date": func.coalesce(
                insert_stmt.excluded.published_date, Manga.published_date
            ),
            "description": func.coalesce(
                insert_stmt.excluded.description, Manga.description
            ),
            "image_url": func.coalesce(insert_stmt.excluded.image_url, Manga.image_url),
            "status": func.coalesce(insert_stmt.excluded.status, Manga.status),
        },
    ).returning(Manga.mal_id, Manga.id)

    # Re-key to get external_id via mal_id
    mal_id_to_manga_id = {mal_id: manga_id for mal_id, manga_id in db.execute(stmt)}
    id_map = {
        r["external_id"]: mal_id_to_manga_id[r["mal_id"]]
        for r in records  # Full input (duplicates need mapping)
        if r["mal_id"] in mal_id_to_manga_id
    }

    return id_map


def bulk_update_or_create_manga(
    db: Session,
    source_id: uuid.UUID,
    records: Sequence[MangaUpsertValues],
) -> dict[str, uuid.UUID]:
    """Upsert a batch of manga records, returning external_id to manga_id.

    Records with a mal_id go through one bulk ON CONFLICT statement. Records
    without one fall back to a slower, per-record upsert. mal_id is the
    cross-source identity key, so checking it first stops the same title
    from being inserted twice as multiple sources are ingested.
    """
    records_with_mal_id = [r for r in records if r["mal_id"] is not None]
    records_without_mal_id = [r for r in records if r["mal_id"] is None]

    return {
        **_bulk_upsert_with_mal_id(db, records_with_mal_id),
        **_bulk_upsert_without_mal_id(db, records_without_mal_id, source_id),
    }


def bulk_add_tags_to_manga(
    db: Session,
    links: Sequence[TagLinkValues],
) -> None:
    """Attach tag links to their manga, merging any that already exist.

    A link without a rank keeps the stored rank, and a spoiler flag never
    clears, so source ingest order does not change the result.
    """
    # Avoid raising CardinalityViolation by deduplicating by both ids.
    by_key: dict[tuple[uuid.UUID, uuid.UUID], TagLinkValues] = {}
    for link in links:
        by_key.setdefault((link["manga_id"], link["tag_id"]), link)

    values = [
        {
            "manga_id": m_id,
            "tag_id": t_id,
            "rank": link["rank"],
            "is_spoiler": link["is_spoiler"],
        }
        for (m_id, t_id), link in by_key.items()
    ]
    if not values:
        return
    insert_stmt = pg_insert(manga_tags).values(values)
    stmt = insert_stmt.on_conflict_do_update(
        index_elements=["manga_id", "tag_id"],
        set_={
            "rank": func.coalesce(insert_stmt.excluded.rank, manga_tags.c.rank),
            "is_spoiler": manga_tags.c.is_spoiler | insert_stmt.excluded.is_spoiler,
        },
    )
    db.execute(stmt)


def bulk_add_authors_to_manga(
    db: Session,
    pairs: Sequence[tuple[uuid.UUID, uuid.UUID]],
) -> None:
    """Attach (manga_id, author_id) pairs, skipping ones that already exist."""
    if not pairs:
        return
    values = [{"manga_id": m, "author_id": a} for m, a in pairs]
    stmt = (
        pg_insert(manga_authors)
        .values(values)
        .on_conflict_do_nothing(index_elements=["manga_id", "author_id"])
    )
    db.execute(stmt)


def delete_orphaned_manga(db: Session) -> int:
    """Delete manga that hold no external rating and return the number removed.

    A re-pointed rating can leave its old manga row behind. Every ingested
    record writes a rating, so a manga without one is unreachable.
    """
    stmt = (
        delete(Manga)
        .where(~exists().where(MangaExternalRating.manga_id == Manga.id))
        .returning(Manga.id)
    )
    return len(db.execute(stmt).all())
