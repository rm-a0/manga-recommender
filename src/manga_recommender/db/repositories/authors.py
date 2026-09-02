"""Data-access functions for the Author model."""

import re
import unicodedata
import uuid
from collections.abc import Sequence

from sqlalchemy import and_, case, func, not_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from manga_recommender.db.models.authors import Author


def get_author_by_id(db: Session, author_id: uuid.UUID) -> Author | None:
    """Return the author with the given ID, or None if not found."""
    return db.scalar(select(Author).where(Author.id == author_id))


def get_all_authors(
    db: Session,
    *,
    limit: int,
    offset: int,
) -> Sequence[Author]:
    """Return one page of authors, ordered by name."""
    return db.scalars(
        select(Author).order_by(Author.name, Author.id).offset(offset).limit(limit)
    ).all()


def count_authors(db: Session) -> int:
    """Return the number of author rows."""
    count = db.scalar(select(func.count()).select_from(Author))
    if not count:
        return 0
    return count


def normalize_author_name(name: str) -> str:
    """Return the key that decides whether two spellings are the same author.

    Sources write one person several ways: "Inoue, Takehiko" and
    "Takehiko Inoue". The key folds case, drops punctuation and accents, and
    sorts the name parts, so both spellings reach it.
    """
    stripped = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    parts = [part for part in re.split(r"[^a-z0-9]+", stripped.lower()) if part]
    return " ".join(sorted(parts))


def create_author(
    db: Session,
    *,
    name: str,
) -> Author:
    """Create and persist a new author."""
    db_author = Author(
        name=name,
        normalized_name=normalize_author_name(name),
    )
    db.add(db_author)
    db.flush()
    return db_author


def get_author_by_name(db: Session, name: str) -> Author | None:
    """Return the author matching the given name, or None if not found.

    Matches on the normalized name, so any spelling of one person finds them.
    """
    return db.scalar(
        select(Author).where(Author.normalized_name == normalize_author_name(name))
    )


def get_or_create_author(
    db: Session,
    *,
    name: str,
) -> Author:
    """Return the existing author with the given name, creating it if needed."""
    author = get_author_by_name(db, name)
    if author:
        return author
    return create_author(db, name=name)


# --- Bulk operations ---


def _is_better_display_name(candidate: str, incumbent: str) -> bool:
    """Return whether the candidate spelling reads better than the incumbent.

    A name without a comma is the natural order, so "Takehiko Inoue" wins over
    "Inoue, Takehiko".
    """
    return "," in incumbent and "," not in candidate


def bulk_get_or_create_authors(
    db: Session,
    names: Sequence[str],
) -> dict[str, uuid.UUID]:
    """Return a mapping of author names to their UUIDs, creating any that don't exist.

    Names that normalize to the same key share one row. A name that normalizes
    to nothing is left out of the result.
    """
    best_by_key: dict[str, str] = {}
    for name in names:
        key = normalize_author_name(name)
        if not key:
            continue
        incumbent = best_by_key.get(key)
        if incumbent is None or _is_better_display_name(name, incumbent):
            best_by_key[key] = name
    if not best_by_key:
        return {}

    values = [{"name": n, "normalized_name": k} for k, n in best_by_key.items()]
    insert_stmt = pg_insert(Author).values(values)
    stmt = insert_stmt.on_conflict_do_update(
        index_elements=["normalized_name"],
        set_={
            # Keep the stored spelling unless the incoming one reads better.
            "name": case(
                (
                    and_(
                        Author.name.like("%,%"),
                        not_(insert_stmt.excluded.name.like("%,%")),
                    ),
                    insert_stmt.excluded.name,
                ),
                else_=Author.name,
            )
        },
    ).returning(Author.normalized_name, Author.id)

    ids_by_key = {key: author_id for key, author_id in db.execute(stmt)}
    return {
        name: ids_by_key[key]
        for name in names
        if (key := normalize_author_name(name)) in ids_by_key
    }
