"""Business logic for the tags resource."""

import uuid

from sqlalchemy.orm import Session

from manga_recommender.db.models.tags import Tag
from manga_recommender.db.repositories.manga import count_manga_by_tag_id
from manga_recommender.db.repositories.tags import (
    count_tags,
    get_all_tags,
    get_tag_by_id,
)
from manga_recommender.schemas.common import Page
from manga_recommender.schemas.tags import TagDetail, TagSummary


def _to_summary(tag: Tag) -> TagSummary:
    """Map a tag row to its list-response model."""
    return TagSummary(id=tag.id, name=tag.name)


def _to_detail(tag: Tag, manga_count: int) -> TagDetail:
    """Map a tag row and its manga count to the single-resource model."""
    return TagDetail(
        id=tag.id,
        name=tag.name,
        category=tag.category,
        manga_count=manga_count,
    )


def get_tag_detail(db: Session, tag_id: uuid.UUID) -> TagDetail | None:
    """Return the full record for one tag, or None if no tag has that ID."""
    tag = get_tag_by_id(db, tag_id)
    if not tag:
        return None
    manga_count = count_manga_by_tag_id(db, tag_id)
    return _to_detail(tag, manga_count)


def get_tags_page(db: Session, *, limit: int, offset: int) -> Page[TagSummary]:
    """Return one page of tag summaries.

    `total` counts every tag, not the items on this page.
    """
    return Page(
        items=[_to_summary(t) for t in get_all_tags(db, limit=limit, offset=offset)],
        total=count_tags(db),
        limit=limit,
        offset=offset,
    )
