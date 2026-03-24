"""Policy: storefront federation is only for customer accounts."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.auth.federated_login import _ensure_customer_for_federated_login


def test_federated_allows_customer():
    _ensure_customer_for_federated_login(SimpleNamespace(identity_kind="customer"))


def test_federated_rejects_staff():
    with pytest.raises(ValueError, match="staff_federation_denied"):
        _ensure_customer_for_federated_login(SimpleNamespace(identity_kind="staff"))
