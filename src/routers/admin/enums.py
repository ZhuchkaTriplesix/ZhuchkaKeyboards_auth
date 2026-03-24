"""Доменные перечисления admin API."""

from __future__ import annotations

from enum import StrEnum


class IdentityKind(StrEnum):
    customer = "customer"
    staff = "staff"
