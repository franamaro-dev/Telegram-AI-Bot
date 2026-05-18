"""Typed application settings.

Secrets are read from the environment (or a local ``.env``). No real
credentials live in source: defaults are empty and the app refuses to
talk to OpenAI/Telegram unless they are explicitly configured.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "Telegram AI Assistant Webhook"

    # --- Secrets (must come from env in any real deployment) -----------
    TELEGRAM_BOT_TOKEN: str = ""
    OPENAI_API_KEY: str = ""

    # Shared secret echoed by Telegram in the
    # ``X-Telegram-Bot-Api-Secret-Token`` header. When set, the webhook
    # rejects any request that does not present it.
    TELEGRAM_WEBHOOK_SECRET: str = ""

    PUBLIC_WEBHOOK_URL: str = "https://your-domain.example/webhook"

    # --- LLM behaviour -------------------------------------------------
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_TIMEOUT_SECONDS: float = 15.0
    OPENAI_MAX_RETRIES: int = 3
    OPENAI_RETRY_BASE_DELAY: float = 0.5  # exponential backoff base

    # --- Outbound Telegram --------------------------------------------
    TELEGRAM_TIMEOUT_SECONDS: float = 10.0
    TELEGRAM_MAX_RETRIES: int = 3

    SYSTEM_PROMPT: str = (
        "You are a helpful and concise Telegram assistant. "
        "Answer accurately in no more than 3 sentences."
    )

    @property
    def is_configured(self) -> bool:
        """True only when both external credentials are present."""
        return bool(self.TELEGRAM_BOT_TOKEN and self.OPENAI_API_KEY)


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so the env is parsed once per process."""
    return Settings()


settings = get_settings()
