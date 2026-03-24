"""Unit tests for PKCE (RFC 7636)."""

from __future__ import annotations

import base64
import hashlib

from src.auth.oauth_logic import verify_pkce_s256


def test_pkce_s256_roundtrip_known_vector() -> None:
    """43-char verifier (RFC 7636 length); challenge = BASE64URL(SHA256(verifier))."""
    verifier = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopq"
    assert len(verifier) == 43
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    assert verify_pkce_s256(verifier, challenge)


def test_pkce_s256_rejects_wrong_verifier() -> None:
    assert not verify_pkce_s256("short", "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM")
