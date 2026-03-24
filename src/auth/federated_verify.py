"""Verify Telegram Login widget payload and Google ID tokens."""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any

import jwt
from jwt import PyJWKClient

_GOOGLE_JWKS = PyJWKClient("https://www.googleapis.com/oauth2/v3/certs")


def verify_telegram_widget(
    data: dict[str, Any], *, bot_token: str, max_age_seconds: int = 86400
) -> bool:
    """https://core.telegram.org/widgets/login#checking-authorization"""
    check_hash = data.get("hash")
    if not check_hash or not bot_token:
        return False
    auth_date = data.get("auth_date")
    if auth_date is not None:
        try:
            ts = int(auth_date)
        except (TypeError, ValueError):
            return False
        if time.time() - ts > max_age_seconds:
            return False
    pairs: list[str] = []
    for k in sorted(data.keys()):
        if k == "hash":
            continue
        v = data[k]
        if v is None:
            continue
        pairs.append(f"{k}={v}")
    data_check_string = "\n".join(pairs)
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    computed = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, str(check_hash))


def decode_google_id_token(id_token: str, *, audiences: list[str]) -> dict[str, Any]:
    """Validate RS256 Google ID token (web / mobile client)."""
    if not audiences:
        msg = "GOOGLE_CLIENT_IDS is not configured"
        raise ValueError(msg)
    signing_key = _GOOGLE_JWKS.get_signing_key_from_jwt(id_token)
    return jwt.decode(
        id_token,
        signing_key.key,
        algorithms=["RS256"],
        audience=audiences,
        issuer=["https://accounts.google.com", "accounts.google.com"],
    )
