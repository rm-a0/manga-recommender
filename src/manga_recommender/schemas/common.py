"""Response models shared by more than one resource."""

from pydantic import BaseModel


class Page[T](BaseModel):
    """One page of items, plus the window that produced it.

    `total` counts every item that matched, not the items in this page.
    """

    items: list[T]
    total: int
    limit: int
    offset: int
