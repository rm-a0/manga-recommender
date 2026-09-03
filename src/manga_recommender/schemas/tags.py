"""Request and response models for the tags resource."""

import uuid

from pydantic import BaseModel


class TagSummary(BaseModel):
    """A tag as it appears in a list, or embedded in another resource."""

    id: uuid.UUID
    name: str


class TagDetail(BaseModel):
    """A tag as it appears in a single-resource response.

    Adds `category` and `manga_count`. The count costs one extra query per
    tag and so is kept out of the list response. The manga themselves are
    their own endpoint, because one tag can hold thousands of them.
    """

    id: uuid.UUID
    name: str
    category: str | None
    manga_count: int
