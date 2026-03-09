from __future__ import annotations

from logging.config import fileConfig
from typing import Any
import os
import sys

from alembic import context
from sqlalchemy import engine_from_config, pool

# Garante que o diretório raiz do projeto (que contém o pacote `backend`)
# esteja no sys.path, para que `import backend` funcione ao rodar o Alembic.
# Este arquivo está em backend/alembic/env.py, então subimos dois níveis
# para chegar em backend/ e mais um para chegar na raiz do projeto.
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.config import settings
from backend.database import Base
from backend import models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# O configparser do Alembic trata "%" como interpolação.
# Senhas URL-encoded podem conter "%21", então escapamos para "%%21".
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
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
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

