"""HTTP routes for the tag resource."""

import uuid

from fastapi import APIRouter, HTTPException, status

from manga_recommender.api.dependencies import DbSession, Pagination
from manga_recommender.schemas.common import Page
from manga_recommender.schemas.manga import MangaSummary
from manga_recommender.schemas.tags import TagDetail, TagSummary
from manga_recommender.services.manga import get_manga_page_by_tag_id
from manga_recommender.services.tags import get_tag_detail, get_tags_page

router: APIRouter = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=Page[TagSummary])
def list_tags(db: DbSession, page: Pagination) -> Page[TagSummary]:
    """Return one page of tag summaries."""
    return get_tags_page(db, limit=page.limit, offset=page.offset)


@router.get("/{tag_id}", response_model=TagDetail)
def get_tag(db: DbSession, tag_id: uuid.UUID) -> TagDetail:
    """Return the full record for one tag.

    An ID that matches no tag gives a 404 response.
    """
    tag_detail = get_tag_detail(db, tag_id)
    if not tag_detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tag with ID {tag_id} not found",
        )
    return tag_detail


@router.get("/{tag_id}/manga", response_model=Page[MangaSummary])
def list_tagged_manga(
    db: DbSession,
    tag_id: uuid.UUID,
    page: Pagination,
) -> Page[MangaSummary]:
    """Return one page of the manga that carry one tag.

    An ID that matches no tag gives an empty page rather than a 404,
    because the collection of that tag's manga is genuinely empty.
    """
    return get_manga_page_by_tag_id(
        db,
        tag_id,
        limit=page.limit,
        offset=page.offset,
    )
