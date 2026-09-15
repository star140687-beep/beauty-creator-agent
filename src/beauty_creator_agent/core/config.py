from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/beauty_agent"
    checkpoint_backend: Literal["memory", "postgres"] = "memory"
    research_backend: Literal["sample", "database"] = "sample"
    llm_provider: Literal["ollama", "fake"] = "ollama"
    llm_base_url: str = "http://127.0.0.1:11434"
    llm_api_key: str | None = Field(default=None, repr=False)
    planner_model: str = "llama3.2:3b"
    writer_model: str = "qwen2.5:14b"
    compliance_model: str = "llama3.2:3b"
    ollama_keep_alive: str = "15m"
    embedding_model: str | None = None
    embedding_dim: int | None = Field(default=None, gt=0)
    max_revision_count: int = Field(default=2, ge=0, le=10)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    trend_provider: str = "none"

    @field_validator("embedding_dim", mode="before")
    @classmethod
    def blank_embedding_dim_is_unset(cls, value: object) -> object:
        """Allow an intentionally blank optional value in a local `.env` file."""
        return None if value == "" else value

    @field_validator("llm_api_key", "embedding_model", mode="before")
    @classmethod
    def blank_optional_strings_are_unset(cls, value: object) -> object:
        return None if value == "" else value


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance for the current process."""
    return Settings()
