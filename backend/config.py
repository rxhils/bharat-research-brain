from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    postgres_url: str
    redis_url: str = "redis://localhost:6379/0"
    ollama_host: str = "http://localhost:11434"
    log_format: str = "console"
    tz: str = "Asia/Kolkata"
    live_feed_mode: str = "demo"  # 'demo' (synthetic ticks) | 'fyers' (broker WS)
    newsapi_key: str = ""  # optional; RSS works without it
    marketaux_key: str = ""  # optional; RSS works without it
    yfinance_price_fallback: bool = True  # nightly EOD fill when bhavcopy absent

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# All fields are populated from the environment / .env at runtime, so no
# arguments are passed here. `type: ignore[call-arg]` silences mypy's
# false positive — pydantic-settings does not require them at the call site.
settings = Settings()  # type: ignore[call-arg]
