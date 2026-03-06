from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_NAME: str = "SmartRecruitz Interview Question Agent"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    API_PREFIX: str = "/api"

    DATABASE_URL: str = "sqlite+aiosqlite:///./interview_agent.db"

    AI_PROVIDER: Literal["openai", "anthropic", "mock"] = "mock"
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-latest"

    DEFAULT_TOTAL_QUESTIONS: int = 12
    DEFAULT_SIMILARITY_THRESHOLD: float = Field(default=0.70, ge=0.0, le=1.0)
    QUESTION_LOOKBACK_DAYS: int = 30
    MAX_REGEN_ATTEMPTS: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
