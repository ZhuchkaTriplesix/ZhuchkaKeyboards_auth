"""JWT access tokens (RS256) and JWKS."""

from __future__ import annotations

import base64
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from src.config import auth_cfg


_KID = "auth-rs256-1"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _ensure_private_key_pem() -> bytes:
    env_pem = os.environ.get("AUTH_JWT_PRIVATE_KEY_PEM", "").strip()
    if env_pem:
        return env_pem.encode()

    path = Path(auth_cfg.jwt_private_key_path)
    if not path.is_absolute():
        path = _repo_root() / path
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        path.write_bytes(pem)
    return path.read_bytes()


_private_pem: bytes | None = None


def private_key_pem() -> bytes:
    global _private_pem
    if _private_pem is None:
        _private_pem = _ensure_private_key_pem()
    return _private_pem


def public_key_pem() -> bytes:
    priv = serialization.load_pem_private_key(private_key_pem(), password=None)
    pub = priv.public_key()
    return pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def jwks_document() -> dict[str, Any]:
    pub = serialization.load_pem_private_key(private_key_pem(), password=None).public_key()
    numbers = pub.public_numbers()
    def b64u(data: int) -> str:
        length = (data.bit_length() + 7) // 8
        b = data.to_bytes(length, byteorder="big")
        return base64.urlsafe_b64encode(b).decode().rstrip("=")

    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": _KID,
                "use": "sig",
                "alg": "RS256",
                "n": b64u(numbers.n),
                "e": b64u(numbers.e),
            }
        ]
    }


def mint_access_token(
    *,
    sub: str,
    scope: str,
    client_id: str,
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, int]:
    now = datetime.now(tz=UTC)
    exp = now + timedelta(minutes=auth_cfg.access_token_minutes)
    payload: dict[str, Any] = {
        "iss": auth_cfg.issuer.rstrip("/"),
        "sub": sub,
        "aud": auth_cfg.audience,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "scope": scope,
        "client_id": client_id,
        "token_use": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    token = jwt.encode(
        payload,
        private_key_pem(),
        algorithm="RS256",
        headers={"kid": _KID, "typ": "JWT"},
    )
    ttl = int((exp - now).total_seconds())
    return token, ttl


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        public_key_pem(),
        algorithms=["RS256"],
        audience=auth_cfg.audience,
        issuer=auth_cfg.issuer.rstrip("/"),
    )
