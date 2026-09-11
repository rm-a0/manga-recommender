"""SQLAlchemy declarative models."""

from manga_recommender.db.models.authors import Author
from manga_recommender.db.models.manga import Manga
from manga_recommender.db.models.manga_embeddings import MangaEmbedding
from manga_recommender.db.models.manga_external_ratings import MangaExternalRating
from manga_recommender.db.models.manga_metrics import MangaMetric
from manga_recommender.db.models.sources import Source
from manga_recommender.db.models.tags import Tag
from manga_recommender.db.models.users import User

__all__ = [
    "Author",
    "Manga",
    "MangaExternalRating",
    "MangaMetric",
    "Source",
    "Tag",
    "User",
    "MangaEmbedding",
]
