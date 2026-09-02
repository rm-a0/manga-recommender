"""Business logic for the authors resource."""

import uuid

from sqlalchemy.orm import Session

from manga_recommender.db.models.authors import Author
from manga_recommender.db.repositories.authors import (
    count_authors,
    get_all_authors,
    get_author_by_id,
)
from manga_recommender.db.repositories.manga import count_manga_by_author_id
from manga_recommender.schemas.authors import AuthorDetail, AuthorSummary
from manga_recommender.schemas.common import Page


def _to_summary(author: Author) -> AuthorSummary:
    """Map an author row to its list-response model."""
    return AuthorSummary(
        id=author.id,
        name=author.name,
    )


def _to_detail(author: Author, manga_count: int) -> AuthorDetail:
    """Map an author row and its manga count to the single-resource model."""
    return AuthorDetail(
        id=author.id,
        name=author.name,
        manga_count=manga_count,
    )


def get_authors_page(
    db: Session,
    *,
    limit: int,
    offset: int,
) -> Page[AuthorSummary]:
    """Return one page of author summaries.

    `total` counts every author, not the items on this page.
    """
    return Page(
        items=[_to_summary(a) for a in get_all_authors(db, limit=limit, offset=offset)],
        total=count_authors(db),
        limit=limit,
        offset=offset,
    )


def get_author_detail(db: Session, author_id: uuid.UUID) -> AuthorDetail | None:
    """Return the full record for one author, or None if no author has that ID."""
    author = get_author_by_id(db, author_id)
    if not author:
        return None
    return _to_detail(author, count_manga_by_author_id(db, author_id))
