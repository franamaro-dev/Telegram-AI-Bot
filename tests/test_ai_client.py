from __future__ import annotations

import httpx
import pytest
from openai import APITimeoutError

import bot.ai_client as ai


class _Msg:
    def __init__(self, content: str | None) -> None:
        self.message = type("M", (), {"content": content})()


class _Completion:
    def __init__(self, content: str | None) -> None:
        self.choices = [_Msg(content)]


class _FakeCompletions:
    def __init__(self, behaviour) -> None:
        self._behaviour = behaviour
        self.calls = 0

    async def create(self, **kwargs):
        self.calls += 1
        return await self._behaviour(self.calls, kwargs)


class _FakeClient:
    def __init__(self, behaviour) -> None:
        self.chat = type("C", (), {"completions": _FakeCompletions(behaviour)})()


def _install_client(monkeypatch, behaviour) -> _FakeClient:
    fake = _FakeClient(behaviour)
    monkeypatch.setattr(ai, "_client", lambda: fake)
    return fake


@pytest.mark.asyncio
async def test_generate_ai_response_success(monkeypatch):
    async def ok(_calls, _kwargs):
        return _Completion("  hello world  ")

    _install_client(monkeypatch, ok)
    assert await ai.generate_ai_response("hi") == "hello world"


@pytest.mark.asyncio
async def test_generate_ai_response_retries_then_succeeds(monkeypatch):
    async def flaky(calls, _kwargs):
        if calls < 2:
            raise APITimeoutError(request=httpx.Request("POST", "http://x"))
        return _Completion("recovered")

    fake = _install_client(monkeypatch, flaky)
    assert await ai.generate_ai_response("hi") == "recovered"
    assert fake.chat.completions.calls == 2


@pytest.mark.asyncio
async def test_generate_ai_response_transient_exhausted_raises(monkeypatch):
    async def always_timeout(_calls, _kwargs):
        raise APITimeoutError(request=httpx.Request("POST", "http://x"))

    _install_client(monkeypatch, always_timeout)
    with pytest.raises(ai.AIServiceError):
        await ai.generate_ai_response("hi")


@pytest.mark.asyncio
async def test_empty_completion_is_an_error(monkeypatch):
    async def empty(_calls, _kwargs):
        return _Completion(None)

    _install_client(monkeypatch, empty)
    with pytest.raises(ai.AIServiceError):
        await ai.generate_ai_response("hi")


@pytest.mark.asyncio
async def test_send_telegram_requires_token(monkeypatch):
    monkeypatch.setattr(ai.settings, "TELEGRAM_BOT_TOKEN", "")
    with pytest.raises(ai.TelegramDeliveryError):
        await ai.send_telegram_message(1, "hi")


@pytest.mark.asyncio
async def test_send_telegram_success(monkeypatch):
    monkeypatch.setattr(ai.settings, "TELEGRAM_BOT_TOKEN", "T:OKEN")

    sent: list[dict] = []

    async def fake_post(self, url, json):
        sent.append(json)
        return httpx.Response(200, text="ok")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    await ai.send_telegram_message(99, "reply")
    assert sent == [{"chat_id": 99, "text": "reply", "parse_mode": "Markdown"}]


@pytest.mark.asyncio
async def test_send_telegram_4xx_raises(monkeypatch):
    monkeypatch.setattr(ai.settings, "TELEGRAM_BOT_TOKEN", "T:OKEN")

    async def fake_post(self, url, json):
        return httpx.Response(400, text="bad request")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    with pytest.raises(ai.TelegramDeliveryError):
        await ai.send_telegram_message(1, "x")
