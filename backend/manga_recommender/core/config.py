"""Load application settings from environment variables."""

import functools
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class _EnvSettings(BaseSettings):
    """Base for every settings class: read `.env`, ignore unknown keys.

    A subclass sets only its `env_prefix`. Pydantic merges the two configs.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class AppSettings(_EnvSettings):
    """General application settings."""

    title: str = "manga-rec"
    version: str = "0.1.0"
    env: str = "development"
    debug: bool = True

    model_config = SettingsConfigDict(env_prefix="APP_")


class LoggingSettings(_EnvSettings):
    """Logging settings."""

    level: str = "INFO"

    model_config = SettingsConfigDict(env_prefix="LOGGING_")


class DatabaseSettings(_EnvSettings):
    """Database connection settings."""

    use_pooled: bool = False
    url: str = "postgresql://postgres:password@localhost:5432/mydb"
    url_pooled: str | None = None
    pool_size: int = 5
    max_overflow: int = 10
    statement_timeout: int | None = None  # Milliseconds

    model_config = SettingsConfigDict(env_prefix="DB_")

    @model_validator(mode="after")
    def _require_pooled_url(self) -> DatabaseSettings:
        """Reject `use_pooled` when no pooled URL is configured to connect to."""
        if self.use_pooled and not self.url_pooled:
            raise ValueError("DB_USE_POOLED is true but DB_URL_POOLED is not set")
        return self

    @property
    def effective_url(self) -> str:
        """Return the URL the application connects with.

        Migrations and ingestion read `url` directly instead. Both need
        session-level features, which a transaction pooler cannot give them.
        """
        if self.use_pooled and self.url_pooled:
            return self.url_pooled
        return self.url


class APISettings(_EnvSettings):
    """API server bind settings."""

    host: str = "0.0.0.0"
    port: int = 8000

    model_config = SettingsConfigDict(env_prefix="API_")


class AnilistSettings(_EnvSettings):
    """AniList API and crawl settings, shared by every AniList ingest."""

    base_url: str = "https://graphql.anilist.co"
    requests_per_minute: int = 30
    catalog_chunk_size: int = 50
    community_recs_chunk_size: int = 50
    min_id: int = 30001  # No manga below this ID
    max_id: int | None = None  # None = fetch all

    model_config = SettingsConfigDict(env_prefix="ANILIST_")


class KaggleMalSettings(_EnvSettings):
    """Kaggle MAL extractor settings."""

    path: str = "data/kaggle_mal_2026.csv"
    dataset_url: str = (
        "https://www.kaggle.com/datasets/patelris/anime-and-manga-dataset-2026"
    )

    model_config = SettingsConfigDict(env_prefix="KAGGLE_MAL_")


class IngestionSettings(_EnvSettings):
    """Ingestion settings."""

    db_batch_size: int = 50

    model_config = SettingsConfigDict(env_prefix="INGESTION_")


class PipelineSettings(_EnvSettings):
    """Pipeline stage settings. File locations live in `StorageSettings`."""

    smoothing_votes: float = 250.0
    db_batch_size: int = 5000
    parquet_batch_size: int = 5000
    encode_batch_size: int = 256
    min_description_length: int = 100
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_device: str | None = None

    model_config = SettingsConfigDict(env_prefix="PIPELINE_")


class StorageSettings(_EnvSettings):
    """Where every raw dataset and artifact lives."""

    community_recs_path: Path = Path("data/raw/anilist/community_recs")
    manga_snapshot_path: Path = Path("data/artifacts/manga.parquet")
    embeddings_path: Path = Path("data/artifacts/embeddings.npz")

    model_config = SettingsConfigDict(env_prefix="STORAGE_")


@functools.lru_cache
def get_app_settings() -> AppSettings:
    """Return the cached AppSettings instance."""
    return AppSettings()


@functools.lru_cache
def get_logging_settings() -> LoggingSettings:
    """Return the cached LoggingSettings instance."""
    return LoggingSettings()


@functools.lru_cache
def get_database_settings() -> DatabaseSettings:
    """Return the cached DatabaseSettings instance."""
    return DatabaseSettings()


@functools.lru_cache
def get_api_settings() -> APISettings:
    """Return the cached APISettings instance."""
    return APISettings()


@functools.lru_cache
def get_anilist_settings() -> AnilistSettings:
    """Return the cached AnilistSettings instance."""
    return AnilistSettings()


@functools.lru_cache
def get_kaggle_mal_settings() -> KaggleMalSettings:
    """Return the cached KaggleMalSettings instance."""
    return KaggleMalSettings()


@functools.lru_cache
def get_ingestion_settings() -> IngestionSettings:
    """Return the cached IngestionSettings instance."""
    return IngestionSettings()


@functools.lru_cache
def get_pipeline_settings() -> PipelineSettings:
    """Return the cached PipelineSettings instance."""
    return PipelineSettings()


@functools.lru_cache
def get_storage_settings() -> StorageSettings:
    """Return the cached StorageSettings instance."""
    return StorageSettings()
