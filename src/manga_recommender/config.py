"""Load application settings from environment variables."""

import functools

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """General application settings."""

    env: str = "development"
    debug: bool = True

    model_config = SettingsConfigDict(
        env_prefix="APP_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class LoggingSettings(BaseSettings):
    """Logging settings."""

    level: str = "INFO"

    model_config = SettingsConfigDict(
        env_prefix="LOGGING_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class DatabaseSettings(BaseSettings):
    """Database connection settings."""

    url: str = "postgresql://postgres:password@localhost:5432/mydb"
    url_pooled: str = "postgresql://postgres:password@localhost:6543/mydb"

    model_config = SettingsConfigDict(
        env_prefix="DB_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class APISettings(BaseSettings):
    """API server bind settings."""

    host: str = "0.0.0.0"
    port: int = 8000

    model_config = SettingsConfigDict(
        env_prefix="API_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class AniListSettings(BaseSettings):
    """AniList extractor settings."""

    base_url: str = "https://graphql.anilist.co"
    requests_per_minute: int = 30
    chunk_size: int = 50
    min_id: int = 30001  # No manga below this ID
    max_id: int | None = None  # None = fetch all

    model_config = SettingsConfigDict(
        env_prefix="ANILIST_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class IngestionSettings(BaseSettings):
    """Ingestion pipeline settings."""

    batch_size: int = 50

    model_config = SettingsConfigDict(
        env_prefix="INGESTION_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


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
def get_anilist_settings() -> AniListSettings:
    """Return the cached AniListSettings instance."""
    return AniListSettings()


@functools.lru_cache
def get_ingestion_settings() -> IngestionSettings:
    """Return the cached IngestionSettings instance."""
    return IngestionSettings()
