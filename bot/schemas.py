"""Pydantic models for the slice of the Telegram Bot API we consume.

Telegram updates are large and polymorphic. We model only what the bot
acts on and let unknown fields pass through, so a payload shape change
upstream does not crash the webhook — it is parsed, found irrelevant,
and acknowledged.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class TelegramChat(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int


class TelegramMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    message_id: int
    chat: TelegramChat
    text: str | None = None


class TelegramUpdate(BaseModel):
    """A single incoming update. Only text messages are actionable."""

    model_config = ConfigDict(extra="ignore")

    update_id: int
    message: TelegramMessage | None = None

    @property
    def actionable_text(self) -> tuple[int, str] | None:
        """Return ``(chat_id, text)`` if this update is a text message."""
        if self.message and self.message.text:
            return self.message.chat.id, self.message.text
        return None
