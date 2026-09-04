"""Request and response models shared by more than one resource."""

from enum import StrEnum

from pydantic import BaseModel, Field


class SortOrder(StrEnum):
    """Direction of a sorted list endpoint."""

    ASC = "asc"
    DESC = "desc"


class PageParams(BaseModel):
    """Limit and offset for a paginated list endpoint."""

    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class Page[T](BaseModel):
    """One page of items, plus the window that produced it.

    `total` counts every item that matched, not the items in this page.
    """

    items: list[T]
    total: int
    limit: int
    offset: int
