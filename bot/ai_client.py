"""External integrations: OpenAI (LLM) and Telegram (outbound).

Both calls are wrapped with bounded timeouts and exponential-backoff
retries on *transient* failures only. Permanent failures (bad key,
4xx) are not retried. Every path either returns a valid result or
raises a typed error — nothing fails silently.
"""

from __future__ import annotations

import logging

import httpx
from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from bot.config import settings

logger = logging.getLogger(__name__)


class AIServiceError(RuntimeError):
    """The LLM call could not be completed after retries."""


class TelegramDeliveryError(RuntimeError):
    """A reply could not be delivered to Telegram after retries."""


# Lazily instantiated so the app can import/boot without secrets
# (e.g. during tests or a health check on a misconfigured deploy).
_openai_client: AsyncOpenAI | None = None


def _client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        if not settings.OPENAI_API_KEY:
            raise AIServiceError("OPENAI_API_KEY is not configured")
        _openai_client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.OPENAI_TIMEOUT_SECONDS,
            max_retries=0,  # we own the retry policy via tenacity
        )
    return _openai_client


_TRANSIENT_OPENAI = (APITimeoutError, APIConnectionError, RateLimitError)


@retry(
    retry=retry_if_exception_type(_TRANSIENT_OPENAI),
    stop=stop_after_attempt(settings.OPENAI_MAX_RETRIES),
    wait=wait_exponential(multiplier=settings.OPENAI_RETRY_BASE_DELAY, max=8),
    reraise=True,
)
async def _call_openai(user_message: str) -> str:
    completion = await _client().chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": settings.SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    content = completion.choices[0].message.content
    if not content:
        raise AIServiceError("OpenAI returned an empty completion")
    return content.strip()


async def generate_ai_response(user_message: str) -> str:
    """Return the model reply, or raise :class:`AIServiceError`.

    Transient errors are retried with exponential backoff. Permanent
    errors (auth, malformed request) fail fast.
    """
    try:
        return await _call_openai(user_message)
    except _TRANSIENT_OPENAI as exc:
        logger.error("OpenAI transient failure after retries: %s", exc)
        raise AIServiceError("LLM temporarily unavailable") from exc
    except APIError as exc:  # permanent: do not retry
        logger.error("OpenAI permanent error: %s", exc)
        raise AIServiceError("LLM request rejected") from exc


@retry(
    retry=retry_if_exception_type(httpx.TransportError),
    stop=stop_after_attempt(settings.TELEGRAM_MAX_RETRIES),
    wait=wait_exponential(multiplier=0.5, max=8),
    reraise=True,
)
async def _post_telegram(client: httpx.AsyncClient, url: str, payload: dict) -> None:
    response = await client.post(url, json=payload)
    if response.status_code >= 500:
        # Server-side: transient, let tenacity retry.
        raise httpx.TransportError(f"Telegram 5xx: {response.status_code}")
    if response.status_code != 200:
        # Client-side (4xx): permanent, surface immediately.
        raise TelegramDeliveryError(
            f"Telegram rejected message ({response.status_code}): {response.text}"
        )


async def send_telegram_message(chat_id: int, text: str) -> None:
    """Deliver ``text`` to ``chat_id``; raise on unrecoverable failure."""
    if not settings.TELEGRAM_BOT_TOKEN:
        raise TelegramDeliveryError("TELEGRAM_BOT_TOKEN is not configured")

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}

    timeout = httpx.Timeout(settings.TELEGRAM_TIMEOUT_SECONDS)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            await _post_telegram(client, url, payload)
    except httpx.TransportError as exc:
        logger.error("Telegram delivery failed after retries: %s", exc)
        raise TelegramDeliveryError("Telegram unreachable") from exc
