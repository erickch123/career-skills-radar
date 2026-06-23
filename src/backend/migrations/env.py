import os
import sys
from logging.config import fileConfig
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool
from alembic import context

# Make sure src/backend is on the path so models can import from db
sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env")

from db import Base  # noqa: E402
import models.models  # noqa: F401 — registers all models on Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override sqlalchemy.url from DATABASE_URL env var — never hardcode credentials
database_url = os.environ.get("DATABASE_URL")
if database_url:
    # configparser uses % for interpolation — escape any % in the URL (e.g. %40 for @ in passwords)
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))


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


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
