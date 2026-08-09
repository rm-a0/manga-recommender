"""User ORM model and role enum."""

from enum import StrEnum

from sqlalchemy import Enum
from sqlalchemy.orm import Mapped, mapped_column

from manga_recommender.db.base import Base, enum_values


class UserRole(StrEnum):
    """Permission role assigned to a user."""

    ADMIN = "admin"
    USER = "user"


class User(Base):
    """ORM model for a registered user."""

    __tablename__ = "users"

    name: Mapped[str] = mapped_column()
    email: Mapped[str] = mapped_column(unique=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=enum_values)
    )
