"""Tag ORM model and its many-to-many link to manga."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, ForeignKey, Integer, Table, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from manga_recommender.db.base import Base

if TYPE_CHECKING:
    from manga_recommender.db.models.manga import Manga

manga_tags = Table(
    "manga_tags",
    Base.metadata,
    Column(
        "manga_id",
        ForeignKey("manga.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    # The primary key index leads with manga_id, so it cannot serve a lookup
    # by tag_id alone. That lookup needs its own index.
    Column(
        "tag_id",
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    ),
    # A NULL rank marks a source that asserts the tag but gives it no weight.
    Column("rank", Integer, nullable=True),
    # server_default, not default: the schema comes from this model, so the
    # database itself must carry the value.
    Column("is_spoiler", Boolean, nullable=False, server_default=false()),
)


class Tag(Base):
    """ORM model for a manga tag.

    `name` is the spelling to show. `normalized_name` is the identity key, so
    one tag written several ways stays one row.
    """

    __tablename__ = "tags"

    name: Mapped[str] = mapped_column()
    normalized_name: Mapped[str] = mapped_column(unique=True, index=True)
    category: Mapped[str | None] = mapped_column()
    manga: Mapped[list[Manga]] = relationship(
        secondary=manga_tags, back_populates="tags"
    )
