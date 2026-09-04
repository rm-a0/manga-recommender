"""HTTP routes for the manga resource."""

import uuid

from fastapi import APIRouter, HTTPException, status

from manga_recommender.api.dependencies import DbSession, MangaQuery
from manga_recommender.schemas.common import Page
from manga_recommender.schemas.manga import MangaDetail, MangaSummary
from manga_recommender.services.manga import get_manga_detail, get_manga_page

router: APIRouter = APIRouter(prefix="/manga", tags=["manga"])


@router.get("", response_model=Page[MangaSummary])
def list_manga(db: DbSession, params: MangaQuery) -> Page[MangaSummary]:
    """Return one page of manga summaries."""
    return get_manga_page(db, params)


@router.get("/{manga_id}", response_model=MangaDetail)
def get_manga(db: DbSession, manga_id: uuid.UUID) -> MangaDetail:
    """Return the full record for one manga.

    An ID that matches no manga gives a 404 response.
    """
    manga_detail = get_manga_detail(db, manga_id)
    if not manga_detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Manga with ID {manga_id} not found",
        )
    return manga_detail
