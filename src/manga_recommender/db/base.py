"""Shared SQLAlchemy declarative base and column helpers."""

import uuid
from enum import Enum

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def enum_values(enum_class: type[Enum]) -> list[str]:
    """Return the string values of an enum's members.

    Use this as SQLAlchemy's `values_callable` so enum columns store values, not names.
    """
    return [e.value for e in enum_class]


class Base(DeclarativeBase):
    """Declarative base that gives every model a UUID primary key."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
