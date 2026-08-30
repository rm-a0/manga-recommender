"""Shared FastAPI dependencies for route handlers."""

from typing import Annotated

from fastapi import Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from manga_recommender.db.session import get_db


class PageParams(BaseModel):
    """Limit and offset for a paginated list endpoint."""

    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


Pagination = Annotated[PageParams, Query()]
DbSession = Annotated[Session, Depends(get_db)]
