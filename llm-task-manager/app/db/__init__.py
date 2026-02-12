"""
Package `app.db` : configuration et accès base de données.

- `config.get_database_url` : résolution de l'URL de connexion
- `config.is_sqlite` : détection du backend SQLite (dev local)
- `session.engine` : moteur SQLModel / SQLAlchemy
- `session.get_db_session` : dépendence FastAPI pour obtenir une session
"""

from .config import get_database_url, is_sqlite  # noqa: F401
from .session import engine, get_db_session, init_db  # noqa: F401

__all__ = ["engine", "get_db_session", "init_db", "get_database_url", "is_sqlite"]

