"""Alembic env.py — async-capable, reads DATABASE_URL from app.config.Settings.

This is the standard Alembic pattern for async engines:
we create the async engine, wrap it in a sync connection via
engine.connect(), and use run_sync inside the MigrationContext.

importlib path trick: ``from alembic import context`` is required by
Alembic's ``alembic`` CLI — it monkeypatches this module at import time.
"""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Add the project root to sys.path so ``from app.config import ...`` works
# regardless of the working directory.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings           # noqa: E402
from app.models import *                       # noqa: E402,F401  — registers all tables on metadata
from sqlmodel import SQLModel                  # noqa: E402

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set sqlalchemy.url at runtime from the app's Settings, not from alembic.ini.
# This ensures Alembic always talks to the same database the app uses.
settings = get_settings()
# Alembic's run_migrations_online expects a *sync* driver URL for the
# configure() call, but we're using asyncpg.  We swap to the psycopg
# (sync) driver for Alembic so migrations run synchronously — which is
# exactly what Alembic's ``run_sync`` expects.
_sync_url = settings.DATABASE_URL.replace(
    "postgresql+asyncpg://", "postgresql+psycopg://"
).replace(
    "postgresql://", "postgresql+psycopg://"
)
config.set_main_option("sqlalchemy.url", _sync_url)

# Target metadata for --autogenerate support
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — generate SQL without a live connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using an async engine wrapped in sync."""
    # Rebuild the URL to use the async driver for the actual connection
    _async_url = settings.DATABASE_URL
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        # Override the URL to use async driver
        url=_async_url,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
