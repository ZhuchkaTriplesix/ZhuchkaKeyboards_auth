"""Domain models align with Alembic migrations (issue #3)."""

from src.auth.db_models import ExternalIdentity, LoginAudit, OAuthClient, User


def test_user_has_identity_kind_column():
    names = {c.name for c in User.__table__.columns}
    assert "identity_kind" in names


def test_login_audit_has_login_method():
    names = {c.name for c in LoginAudit.__table__.columns}
    assert "login_method" in names


def test_external_identity_table_name():
    assert ExternalIdentity.__table__.name == "external_identity"


def test_oauth_client_table_name():
    assert OAuthClient.__table__.name == "oauth_client"
