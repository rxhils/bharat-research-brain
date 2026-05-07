from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    postgres_url: str
    redis_url: str = "redis://localhost:6379/0"
    ollama_host: str = "http://localhost:11434"
    finbert_host: str = "http://localhost:8765"
    log_format: str = "console"
    tz: str = "Asia/Kolkata"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
