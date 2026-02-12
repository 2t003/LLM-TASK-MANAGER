"""
Création du moteur SQLModel et gestion des sessions DB.

Cette couche est utilisée par :
- les services applicatifs
- les routes FastAPI (via dépendence ``get_db_session``)

Configuration du pool de connexions (cf. ARCHITECTURE.md) :
- SQLite  : ``StaticPool`` (dev local, pas de pooling)
- PostgreSQL : ``pool_size=5``, ``max_overflow=5``, ``pool_timeout=30``
  Adaptée à Cloud Run (scaling → limiter les connexions simultanées).
"""

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.db.config import get_database_url, is_sqlite


DATABASE_URL = get_database_url()


def _create_engine():
    """
    Crée le moteur SQLAlchemy/SQLModel avec la configuration appropriée
    selon le backend (SQLite dev vs PostgreSQL prod / Cloud Run).
    """
    if is_sqlite():
        # --- SQLite : dev local ---
        return create_engine(
            DATABASE_URL,
            echo=False,
            connect_args={"check_same_thread": False},
        )

    # --- PostgreSQL (Cloud Run / CI) ---
    # Pool adapté à Cloud Run : limiter les connexions simultanées
    # car chaque instance Cloud Run peut scaler indépendamment.
    # Cf. ARCHITECTURE.md § Gestion du pool de connexions
    return create_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,         # Vérifie la connexion avant usage
        pool_size=5,                 # Connexions maintenues dans le pool
        max_overflow=5,              # Connexions supplémentaires temporaires
        pool_timeout=30,             # Timeout d'attente d'une connexion
        pool_recycle=1800,           # Recycle les connexions après 30 min
    )


engine = _create_engine()


def init_db() -> None:
    """
    Initialise le schéma en créant les tables manquantes.

    À utiliser surtout en dev local ; en prod, privilégier les migrations Alembic.
    """
    from app.models.domain import (  # noqa: WPS433,F401
        Comment,
        Document,
        DocumentTemplate,
        Epic,
        Project,
        Sprint,
        Story,
        StorySprintHistory,
    )

    SQLModel.metadata.create_all(bind=engine)


def get_db_session() -> Generator[Session, None, None]:
    """
    Dépendence FastAPI pour obtenir une session DB par requête.
    """
    with Session(engine) as session:
        yield session


__all__ = ["engine", "init_db", "get_db_session"]

