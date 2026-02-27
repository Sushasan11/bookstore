"""Application configuration via pydantic-settings.

Reads configuration from environment variables and .env file.
Use get_settings() (cached) for all config access throughout the app.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@127.0.0.1:5434/bookstore_dev"
    )
    TEST_DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/bookstore_test"
    )

    # Security
    SECRET_KEY: str = "changeme-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # OAuth - Google
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    # Logging
    LOG_LEVEL: str = "INFO"

    # Application
    DEBUG: bool = False
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    ENV: str = "development"

    # Email
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = "noreply@bookstore.com"
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_FROM_NAME: str = "Bookstore"
    MAIL_SUPPRESS_SEND: int = 1  # Default: suppress (safe for dev/test); prod sets to 0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings.

    The @lru_cache ensures .env is read only once per process.
    In tests, call get_settings.cache_clear() to reset after overriding env vars.
    """
    return Settings()
