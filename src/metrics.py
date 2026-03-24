"""Prometheus metrics for auth-service."""

from prometheus_client import Counter

HTTP_REQUESTS_TOTAL = Counter(
    "auth_http_requests_total",
    "Total HTTP requests handled",
    ("method", "status_code"),
)
