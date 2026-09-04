"""Business logic for the manga resource."""

import uuid
from collections.abc import Sequence

from sqlalchemy.orm import Session

from manga_recommender.db.models.manga import Manga
from manga_recommender.db.repositories.manga import (
    MangaFilters,
    TagLink,
    count_manga,
    count_manga_by_author_id,
    count_manga_by_tag_id,
    get_all_manga,
    get_manga_by_author_id,
    get_manga_by_id,
    get_manga_by_tag_id,
    get_manga_tag_links,
)
from manga_recommender.schemas.authors import AuthorSummary
from manga_recommender.schemas.common import Page, SortOrder
from manga_recommender.schemas.manga import (
    MangaDetail,
    MangaListParams,
    MangaSort,
    MangaSummary,
    MangaTag,
    TagMatch,
)


def _to_summary(manga: Manga) -> MangaSummary:
    """Map a manga row to its list-response model.

    Reads `manga.authors`, so the caller must load that relationship first.
    """
    return MangaSummary(
        id=manga.id,
        title=manga.title,
        status=manga.status,
        image_url=manga.image_url,
        authors=[
            AuthorSummary(
                id=a.id,
                name=a.name,
            )
            for a in manga.authors
        ],
    )


def _to_detail(manga: Manga, tag_links: Sequence[TagLink]) -> MangaDetail:
    """Map a manga row to its single-resource response model.

    Reads `manga.authors`, so the caller must load that relationship first.
    """
    return MangaDetail(
        id=manga.id,
        title=manga.title,
        authors=[
            AuthorSummary(
                id=a.id,
                name=a.name,
            )
            for a in manga.authors
        ],
        status=manga.status,
        image_url=manga.image_url,
        published_date=manga.published_date,
        description=manga.description,
        tags=[
            MangaTag(
                id=tag_link.tag.id,
                name=tag_link.tag.name,
                is_spoiler=tag_link.is_spoiler,
                rank=tag_link.rank,
            )
            for tag_link in tag_links
        ],
    )


def _to_terms(query: str | None) -> list[str]:
    """Split a search query into the words a title must all contain.

    An empty or whitespace-only query gives no terms, so it filters nothing.
    """
    if not query:
        return []
    return query.split()


def _to_filters(params: MangaListParams) -> MangaFilters:
    """Map request vocabulary to storage vocabulary.

    Tag names become normalized keys, because the tag table matches on
    `normalized_name` rather than the spelling a source happened to write.
    """
    return MangaFilters(
        title_terms=tuple(_to_terms(params.q)),
        statuses=tuple(params.status),
        include_tag_keys=tuple(t for t in params.include_tag),
        require_all_tags=params.tag_match is TagMatch.ALL,
        exclude_tag_keys=tuple(params.exclude_tag),
        published_from=params.published_from,
        published_to=params.published_to,
    )


def get_manga_page(db: Session, params: MangaListParams) -> Page[MangaSummary]:
    """Return one page of manga summaries.

    `total` counts every manga, not the items on this page.
    """
    filters = _to_filters(params)
    return Page(
        items=[
            _to_summary(m)
            for m in get_all_manga(
                db,
                filters,
                sort=params.sort or MangaSort.TITLE,
                descending=params.order is SortOrder.DESC,
                limit=params.limit,
                offset=params.offset,
            )
        ],
        total=count_manga(db, filters),
        limit=params.limit,
        offset=params.offset,
    )


def get_manga_page_by_author_id(
    db: Session,
    author_id: uuid.UUID,
    *,
    limit: int,
    offset: int,
) -> Page[MangaSummary]:
    """Return one page of the manga credited to one author.

    `total` counts every manga credited to that author, not the items on
    this page. An author with no credits gives an empty page.
    """
    return Page(
        items=[
            _to_summary(m)
            for m in get_manga_by_author_id(db, author_id, limit=limit, offset=offset)
        ],
        total=count_manga_by_author_id(db, author_id),
        limit=limit,
        offset=offset,
    )


def get_manga_page_by_tag_id(
    db: Session,
    tag_id: uuid.UUID,
    *,
    limit: int,
    offset: int,
) -> Page[MangaSummary]:
    """Return one page of the manga that carry one tag.

    `total` counts every manga with that tag, not the items on this page.
    A tag on no manga gives an empty page.
    """
    return Page(
        items=[
            _to_summary(t)
            for t in get_manga_by_tag_id(db, tag_id, limit=limit, offset=offset)
        ],
        total=count_manga_by_tag_id(db, tag_id),
        limit=limit,
        offset=offset,
    )


def get_manga_detail(db: Session, manga_id: uuid.UUID) -> MangaDetail | None:
    """Return the full record for one manga, or None if no manga has that ID."""
    manga = get_manga_by_id(db, manga_id)
    if not manga:
        return None
    return _to_detail(manga, get_manga_tag_links(db, manga_id))
