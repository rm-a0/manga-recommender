"""Request and response models for the manga resource."""

import uuid
from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from manga_recommender.db.models.manga import MangaStatus
from manga_recommender.schemas.authors import AuthorSummary
from manga_recommender.schemas.common import PageParams, SortOrder


class TagMatch(StrEnum):
    """How several tag filters combine: any one of them, or all of them."""

    ANY = "any"
    ALL = "all"


class MangaSort(StrEnum):
    """Field that orders a manga list response."""

    TITLE = "title"
    PUBLISHED_DATE = "published_date"
    # POPULARITY = "popularity"
    # RATING = "rating"
    # RELEVANCE = "relevance"


class MangaListParams(PageParams):
    """Filter, sort and page controls for the manga list endpoint.

    Every field is optional. A request with no query string returns the
    first page, ordered by title.
    """

    q: str | None = Field(None, min_length=2, max_length=100)
    status: list[MangaStatus] = Field(default_factory=list)
    include_tag: list[str] = Field(default_factory=list, max_length=10)
    exclude_tag: list[str] = Field(default_factory=list, max_length=10)
    tag_match: TagMatch = TagMatch.ANY
    published_from: date | None = None
    published_to: date | None = None
    sort: MangaSort | None = None
    order: SortOrder = SortOrder.ASC


class MangaSummary(BaseModel):
    """A manga as it appears in a list response.

    Holds only cheap fields, because one page can hold up to 100 items.
    """

    id: uuid.UUID
    title: str
    authors: list[AuthorSummary]
    status: MangaStatus | None
    image_url: str | None


class MangaTag(BaseModel):
    """A tag as it appears inside a manga response."""

    id: uuid.UUID
    name: str
    is_spoiler: bool
    rank: int | None


class MangaDetail(BaseModel):
    """A manga as it appears in a single-resource response.

    Adds the fields that are too large or too costly to repeat for every
    item in a list.
    """

    id: uuid.UUID
    title: str
    authors: list[AuthorSummary]
    status: MangaStatus | None
    image_url: str | None
    published_date: datetime | None
    description: str | None
    tags: list[MangaTag]
