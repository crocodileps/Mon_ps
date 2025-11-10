"""
Configuration Alembic pour les migrations Mon_PS.
"""
from __future__ import annotations

import logging
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from api.config import settings

# Récupère la configuration Alembic
config = context.config

# Configure le logging si un fichier de configuration est présent
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

# Injecte dynamiquement l'URL de connexion depuis les settings Pydantic
config.set_main_option("sqlalchemy.url", settings.database_url)

# Pas de metadata SQLAlchemy centralisée pour le moment (migrations manuelles)
target_metadata = None


def run_migrations_offline() -> None:
    """Exécute les migrations en mode 'offline'."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Exécute les migrations en mode 'online'."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    logger.info("Exécution des migrations en mode offline")
    run_migrations_offline()
else:
    logger.info("Exécution des migrations en mode online")
    run_migrations_online()

