"""Data-access functions for the Tag model."""

import re
import unicodedata
import uuid
from collections.abc import Sequence
from typing import TypedDict

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from manga_recommender.db.models.tags import Tag


class TagUpsertValues(TypedDict):
    """Column values for one bulk-upserted tag row."""

    name: str
    category: str | None


def get_tag_by_id(db: Session, tag_id: uuid.UUID) -> Tag | None:
    """Return the tag with the given ID, or None if not found."""
    return db.scalar(select(Tag).where(Tag.id == tag_id))


def get_all_tags(
    db: Session,
    *,
    limit: int,
    offset: int,
) -> Sequence[Tag]:
    """Return one page of tags, ordered by name.

    `Tag.id` breaks ties, so a tag cannot repeat across pages or fall
    between them when two share a name.
    """
    return db.scalars(
        select(Tag).order_by(Tag.name, Tag.id).offset(offset).limit(limit)
    ).all()


def count_tags(db: Session) -> int:
    """Return the number of tag rows."""
    count = db.scalar(select(func.count()).select_from(Tag))
    if not count:
        return 0
    return count


def normalize_tag_name(name: str) -> str:
    """Return the key that decides whether two spellings are the same tag.

    Sources write one tag several ways: "Sci-Fi" and "Sci Fi". The key folds
    case, drops accents, and collapses each run of punctuation to one space.
    Word order is kept, because word order carries meaning in a tag.
    """
    stripped = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    parts = [part for part in re.split(r"[^a-z0-9]+", stripped.lower()) if part]
    return " ".join(parts)


def create_tag(
    db: Session,
    *,
    name: str,
    category: str | None,
) -> Tag:
    """Create and persist a new tag."""
    db_tag = Tag(
        name=name,
        normalized_name=normalize_tag_name(name),
        category=category,
    )
    db.add(db_tag)
    db.flush()
    return db_tag


def get_tag_by_name(db: Session, name: str) -> Tag | None:
    """Return the tag matching the given name, or None if not found.

    Matches on the normalized name, so any spelling of one tag finds it.
    """
    return db.scalar(select(Tag).where(Tag.normalized_name == normalize_tag_name(name)))


def get_or_create_tag(
    db: Session,
    *,
    name: str,
    category: str | None,
) -> Tag:
    """Return the existing tag with the given name, creating it if needed."""
    tag = get_tag_by_name(db, name)
    if tag:
        return tag
    return create_tag(db, name=name, category=category)


# --- Bulk operations ---


def bulk_get_or_create_tags(
    db: Session,
    tags: Sequence[TagUpsertValues],
) -> dict[str, uuid.UUID]:
    """Return a mapping of tag names to their UUIDs, creating any that don't exist.

    Names that normalize to the same key share one row, and the first spelling
    wins. A name that normalizes to nothing is left out of the result.
    """
    # A repeated normalized name in one INSERT raises CardinalityViolation.
    by_key: dict[str, TagUpsertValues] = {}
    for t in tags:
        if key := normalize_tag_name(t["name"]):
            by_key.setdefault(key, t)

    values = [
        {
            "name": t["name"],
            "normalized_name": key,
            "category": t["category"],
        }
        for key, t in by_key.items()
    ]
    if not values:
        return {}
    insert_stmt = pg_insert(Tag).values(values)
    # DO UPDATE, not DO NOTHING: only DO UPDATE returns the rows that already
    # existed. COALESCE keeps a category that a later source leaves empty.
    stmt = insert_stmt.on_conflict_do_update(
        index_elements=["normalized_name"],
        set_={
            "category": func.coalesce(insert_stmt.excluded.category, Tag.category),
        },
    ).returning(Tag.normalized_name, Tag.id)
    ids_by_key = {key: tag_id for key, tag_id in db.execute(stmt)}
    return {
        tag["name"]: ids_by_key[key]
        for tag in tags
        if (key := normalize_tag_name(tag["name"])) in ids_by_key
    }
