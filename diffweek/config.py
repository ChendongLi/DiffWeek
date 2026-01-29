"""Configuration settings for DiffWeek."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    github_personal_access_token: Optional[str] = None
    max_diff_lines: int = 500


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
