"""Unit tests for PKCE (RFC 7636)."""

from __future__ import annotations

from src.auth.oauth_logic import verify_pkce_s256


def test_pkce_s256_rfc7636_appendix_b() -> None:
    verifier = "dBjftJeZ4CVP-mB92K27uhbAjtZ2l9J9g0aJqQ1Z9Q"
    challenge = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    assert verify_pkce_s256(verifier, challenge)


def test_pkce_s256_rejects_wrong_verifier() -> None:
    assert not verify_pkce_s256("short", "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM")
