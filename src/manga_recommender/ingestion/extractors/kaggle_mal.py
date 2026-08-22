"""Extractor that pulls manga data from the Kaggle MAL dataset."""

from collections.abc import AsyncIterator

from manga_recommender.config import get_kaggle_mal_settings
from manga_recommender.ingestion.base import BaseExtractor, NormalizedMangaRecord


class KaggleMalExtractor(BaseExtractor):
    """Extracts and normalizes manga data from Kaggle MAL dataset."""

    source_name = "kaggle_mal"

    def __init__(self):
        """Initialize the Kaggle MAL extractor."""
        self.kaggle_mal_settings = get_kaggle_mal_settings()

    async def _stream(self) -> AsyncIterator[NormalizedMangaRecord]:
        """Yield normalized manga records from the Kaggle MAL dataset."""
        raise NotImplementedError("Kaggle MAL extractor is not implemented yet.")
        yield  # This line is just to satisfy the type checker and will never be reached.