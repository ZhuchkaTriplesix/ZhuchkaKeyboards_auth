"""OAuth2 authorization codes (PKCE).

Revision ID: 20250324_0003
Revises: 20250323_0002
Create Date: 2025-03-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "20250324_0003"
down_revision = "20250323_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oauth_authorization_code",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "client_db_id",
            UUID(as_uuid=True),
            sa.ForeignKey("oauth_client.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("redirect_uri", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("code_challenge", sa.String(length=128), nullable=False),
        sa.Column("code_challenge_method", sa.String(length=16), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_oauth_authorization_code_code_hash",
        "oauth_authorization_code",
        ["code_hash"],
        unique=True,
    )
    op.create_index(
        "ix_oauth_authorization_code_expires_at",
        "oauth_authorization_code",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_oauth_authorization_code_expires_at", table_name="oauth_authorization_code")
    op.drop_index("ix_oauth_authorization_code_code_hash", table_name="oauth_authorization_code")
    op.drop_table("oauth_authorization_code")
