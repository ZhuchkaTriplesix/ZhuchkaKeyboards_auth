"""OAuth2 redirect URL helpers (query string merge)."""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def append_query_params(url: str, params: dict[str, str]) -> str:
    """Merge params into the URL query string (fragment preserved)."""
    parts = urlparse(url)
    merged = dict(parse_qsl(parts.query, keep_blank_values=True))
    merged.update(params)
    query = urlencode(sorted(merged.items()))
    return urlunparse(parts._replace(query=query))
