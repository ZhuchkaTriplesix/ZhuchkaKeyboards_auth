"""Domain: user identity_kind, external_identity, login_audit.login_method.

Revision ID: 20250323_0002
Revises: 20250323_0001
Create Date: 2025-03-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "20250323_0002"
down_revision = "20250323_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "identity_kind",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'customer'"),
        ),
    )
    op.add_column(
        "login_audit",
        sa.Column("login_method", sa.String(length=64), nullable=True),
    )
    op.create_table(
        "external_identity",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("provider", "subject", name="uq_external_identity_provider_subject"),
    )
    op.create_index("ix_external_identity_user_id", "external_identity", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_external_identity_user_id", table_name="external_identity")
    op.drop_table("external_identity")
    op.drop_column("login_audit", "login_method")
    op.drop_column("users", "identity_kind")
