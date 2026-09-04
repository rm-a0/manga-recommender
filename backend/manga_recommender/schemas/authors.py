"""Request and response models for the authors resource."""

import uuid

from pydantic import BaseModel


class AuthorSummary(BaseModel):
    """An author as it appears in a list, or embedded in another resource."""

    id: uuid.UUID
    name: str


class AuthorDetail(BaseModel):
    """An author as it appears in a single-resource response.

    Adds `manga_count`, which costs one extra query per author and so is
    kept out of the list response. The manga themselves are their own
    endpoint, because one author can credit hundreds of them.
    """

    id: uuid.UUID
    name: str
    manga_count: int
