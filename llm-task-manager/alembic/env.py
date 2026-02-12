"""
Alembic environment configuration — LLM Task Manager.

Résout l'URL de connexion via app.db.config.get_database_url()
afin de rester cohérent avec la configuration FastAPI (prod / dev).
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from app.db.config import get_database_url

# ---- Alembic Config object ----
config = context.config

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---- Importer TOUS les modèles pour que Alembic les détecte ----
from app.models.domain import (  # noqa: F401,E402
    Comment,
    Document,
    DocumentTemplate,
    Epic,
    Project,
    Sprint,
    Story,
    StorySprintHistory,
)

# Target metadata (SQLModel hérite de SQLAlchemy DeclarativeBase)
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode (génère du SQL sans connexion).
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode (connexion active à la DB).
    """
    # Injecter l'URL résolue dans la config Alembic
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Pas de pool pour les migrations
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
