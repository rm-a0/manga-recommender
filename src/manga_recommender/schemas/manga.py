"""Request and response models for the manga resource."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from manga_recommender.db.models.manga import MangaStatus
from manga_recommender.schemas.authors import AuthorSummary


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
