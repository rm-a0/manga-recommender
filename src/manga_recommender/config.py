import functools

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    env: str = "development"
    debug: bool = True

    model_config = SettingsConfigDict(
        env_prefix="APP_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class DatabaseSettings(BaseSettings):
    url: str = "postgresql://postgres:password@localhost:5432/mydb"
    url_pooled: str = "postgresql://postgres:password@localhost:6543/mydb"

    model_config = SettingsConfigDict(
        env_prefix="DB_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class APISettings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = SettingsConfigDict(
        env_prefix="API_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


@functools.lru_cache
def get_app_settings() -> AppSettings:
    return AppSettings()


@functools.lru_cache
def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings()


@functools.lru_cache
def get_api_settings() -> APISettings:
    return APISettings()
