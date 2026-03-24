"""Unit tests for Telegram / Google verification helpers."""

from __future__ import annotations

import hashlib
import hmac
import time

from src.auth.federated_verify import verify_telegram_widget


def _telegram_hash(data: dict, bot_token: str) -> str:
    pairs = []
    for k in sorted(data.keys()):
        if k == "hash":
            continue
        pairs.append(f"{k}={data[k]}")
    data_check_string = "\n".join(pairs)
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    return hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()


def test_verify_telegram_widget_accepts_valid_payload() -> None:
    bot = "test-bot-token"
    payload = {
        "id": 424242,
        "first_name": "Test",
        "auth_date": int(time.time()),
    }
    payload["hash"] = _telegram_hash(payload, bot)
    assert verify_telegram_widget(payload, bot_token=bot) is True


def test_verify_telegram_widget_rejects_bad_hash() -> None:
    bot = "test-bot-token"
    payload = {
        "id": 1,
        "auth_date": int(time.time()),
        "hash": "deadbeef",
    }
    assert verify_telegram_widget(payload, bot_token=bot) is False


def test_verify_telegram_widget_requires_bot_token() -> None:
    payload = {"id": 1, "auth_date": int(time.time()), "hash": "x"}
    assert verify_telegram_widget(payload, bot_token="") is False
