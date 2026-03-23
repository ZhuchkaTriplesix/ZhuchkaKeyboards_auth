import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import create_async_engine

# Ensure project root is on path when running alembic from repo root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import src.auth.db_models  # noqa: E402, F401
from src.database.base import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _apply_database_url_override() -> None:
    """Prefer DATABASE_URL / ALEMBIC_DATABASE_URL; else build from config.ini (same as the app)."""
    url = os.environ.get("DATABASE_URL") or os.environ.get("ALEMBIC_DATABASE_URL")
    if not url:
        try:
            from src.config import PostgresCfg

            url = PostgresCfg().url
        except Exception:
            return
    if url:
        config.set_main_option("sqlalchemy.url", url)


_apply_database_url_override()

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)


async def run_async_migrations() -> None:
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        raise ValueError("sqlalchemy.url is not set in alembic.ini")

    connectable = create_async_engine(url)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    url = config.get_main_option("sqlalchemy.url") or ""
    if "asyncpg" in url:
        asyncio.run(run_async_migrations())
    else:
        run_migrations_online()
