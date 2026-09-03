"""Shared FastAPI dependencies for route handlers."""

from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from manga_recommender.db.session import get_db
from manga_recommender.schemas.common import PageParams

Pagination = Annotated[PageParams, Query()]
DbSession = Annotated[Session, Depends(get_db)]
