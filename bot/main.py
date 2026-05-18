"""FastAPI webhook entrypoint.

Flow: Telegram -> POST /webhook (validated, ack'd in <1s) -> background
task -> OpenAI -> reply via Telegram. The HTTP handler never blocks on
the LLM, so Telegram's short webhook timeout is always satisfied.
"""

from __future__ import annotations

import logging

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request, status
from pydantic import ValidationError

from bot.ai_client import (
    AIServiceError,
    TelegramDeliveryError,
    generate_ai_response,
    send_telegram_message,
)
from bot.config import settings
from bot.schemas import TelegramUpdate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("telegram_ai_bot")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Event-driven Telegram assistant backed by OpenAI.",
    version="1.0.0",
)

_FALLBACK_REPLY = "I'm having trouble reaching my AI service right now. Please try again shortly."


@app.get("/health")
def health_check() -> dict[str, object]:
    """Liveness + minimal readiness signal (no secrets leaked)."""
    return {
        "status": "ok",
        "service": "Telegram-AI-Bot",
        "configured": settings.is_configured,
    }


async def process_telegram_message(chat_id: int, message_text: str) -> None:
    """Background worker: query the LLM and deliver the reply.

    Runs after the webhook has already returned 200, so Telegram does
    not retry. Degrades gracefully: if the LLM fails, the user still
    gets an explicit message instead of silence.
    """
    try:
        reply = await generate_ai_response(message_text)
    except AIServiceError as exc:
        logger.warning("LLM unavailable for chat %s: %s", chat_id, exc)
        reply = _FALLBACK_REPLY

    try:
        await send_telegram_message(chat_id, reply)
    except TelegramDeliveryError as exc:
        logger.error("Could not deliver reply to chat %s: %s", chat_id, exc)


def _verify_secret(provided: str | None) -> None:
    """Reject forged webhook calls when a shared secret is configured."""
    expected = settings.TELEGRAM_WEBHOOK_SECRET
    if expected and provided != expected:
        logger.warning("Rejected webhook call with invalid secret token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid webhook secret",
        )


@app.post("/webhook")
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, str]:
    """Receive a Telegram update, validate it, ack immediately."""
    _verify_secret(x_telegram_bot_api_secret_token)

    try:
        payload = await request.json()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="invalid JSON"
        )

    try:
        update = TelegramUpdate.model_validate(payload)
    except ValidationError:
        # Unknown/irrelevant shape: acknowledge so Telegram stops
        # retrying, but do no work.
        logger.info("Ignoring non-conforming update")
        return {"status": "ignored"}

    actionable = update.actionable_text
    if actionable is None:
        return {"status": "ignored"}

    chat_id, text = actionable
    background_tasks.add_task(process_telegram_message, chat_id, text)
    return {"status": "accepted"}
