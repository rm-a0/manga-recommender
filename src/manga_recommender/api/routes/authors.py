"""HTTP routes for the authors resource."""

import uuid

from fastapi import APIRouter, HTTPException, status

from manga_recommender.api.dependencies import DbSession, Pagination
from manga_recommender.schemas.authors import AuthorDetail, AuthorSummary
from manga_recommender.schemas.common import Page
from manga_recommender.schemas.manga import MangaSummary
from manga_recommender.services.authors import get_author_detail, get_authors_page
from manga_recommender.services.manga import get_manga_page_by_author_id

router: APIRouter = APIRouter(prefix="/authors", tags=["authors"])


@router.get("", response_model=Page[AuthorSummary])
def list_authors(db: DbSession, page: Pagination) -> Page[AuthorSummary]:
    """Return one page of author summaries."""
    return get_authors_page(db, limit=page.limit, offset=page.offset)


@router.get("/{author_id}", response_model=AuthorDetail)
def get_author(db: DbSession, author_id: uuid.UUID) -> AuthorDetail:
    """Return the full record for one author.

    An ID that matches no author gives a 404 response.
    """
    author_detail = get_author_detail(db, author_id)
    if not author_detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Author with ID {author_id} not found",
        )
    return author_detail


@router.get("/{author_id}/manga", response_model=Page[MangaSummary])
def list_authors_manga(
    db: DbSession,
    author_id: uuid.UUID,
    page: Pagination,
) -> Page[MangaSummary]:
    """Return one page of the manga credited to one author.

    An ID that matches no author gives an empty page rather than a 404,
    because the collection of that author's manga is genuinely empty.
    """
    return get_manga_page_by_author_id(
        db,
        author_id,
        limit=page.limit,
        offset=page.offset,
    )
