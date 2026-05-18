from __future__ import annotations

import bot.main as main


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "configured" in body


def test_text_message_is_accepted_and_scheduled(client, monkeypatch):
    calls: list[tuple[int, str]] = []

    async def fake_process(chat_id: int, text: str) -> None:
        calls.append((chat_id, text))

    monkeypatch.setattr(main, "process_telegram_message", fake_process)

    payload = {
        "update_id": 1,
        "message": {
            "message_id": 10,
            "chat": {"id": 4242},
            "text": "hello bot",
        },
    }
    r = client.post("/webhook", json=payload)
    assert r.status_code == 200
    assert r.json() == {"status": "accepted"}
    assert calls == [(4242, "hello bot")]


def test_non_text_update_is_ignored(client, monkeypatch):
    called = False

    async def fake_process(chat_id: int, text: str) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(main, "process_telegram_message", fake_process)

    payload = {"update_id": 2, "message": {"message_id": 11, "chat": {"id": 1}}}
    r = client.post("/webhook", json=payload)
    assert r.status_code == 200
    assert r.json()["status"] == "ignored"
    assert called is False


def test_malformed_update_is_ignored_not_500(client):
    r = client.post("/webhook", json={"not": "a telegram update"})
    assert r.status_code == 200
    assert r.json()["status"] == "ignored"


def test_invalid_json_returns_400(client):
    r = client.post(
        "/webhook",
        content=b"{ not json",
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 400


def test_webhook_secret_rejected_when_configured(client, monkeypatch):
    # Configure a shared secret on the live settings object.
    monkeypatch.setattr(main.settings, "TELEGRAM_WEBHOOK_SECRET", "s3cret")

    async def fake_process(chat_id: int, text: str) -> None:
        return None

    monkeypatch.setattr(main, "process_telegram_message", fake_process)

    payload = {
        "update_id": 3,
        "message": {"message_id": 1, "chat": {"id": 1}, "text": "hi"},
    }
    # Missing secret -> 401
    assert client.post("/webhook", json=payload).status_code == 401
    # Wrong secret -> 401
    assert (
        client.post(
            "/webhook",
            json=payload,
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
        ).status_code
        == 401
    )
    # Correct secret -> accepted
    ok = client.post(
        "/webhook",
        json=payload,
        headers={"X-Telegram-Bot-Api-Secret-Token": "s3cret"},
    )
    assert ok.status_code == 200
    assert ok.json() == {"status": "accepted"}
