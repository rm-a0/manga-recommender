"""Request and response models for the authors resource."""

import uuid

from pydantic import BaseModel


class AuthorSummary(BaseModel):
    """An author as it appears in a list, or embedded in another resource."""

    id: uuid.UUID
    name: str
