"""
Configuration de la base de données.

Environnement attendu :
- En prod / Cloud Run : variables d'env individuelles pour Cloud SQL :
    DB_USER, DB_PASSWORD, DB_NAME, INSTANCE_CONNECTION_NAME
  Ou bien la variable unique `DATABASE_URL` (PostgreSQL).
  ex: postgresql+psycopg://user:password@/db?host=/cloudsql/INSTANCE_CONNECTION_NAME
- En local (défaut): SQLite fichier `llm_task_manager.db` dans le répertoire courant.

Cf. ARCHITECTURE.md § Stratégie de connexion Cloud Run → Cloud SQL
"""

from functools import lru_cache
import os
from urllib.parse import quote_plus


def _build_cloudsql_url() -> str | None:
    """
    Construit une URL PostgreSQL Cloud SQL à partir de variables d'env
    individuelles (approche recommandée sur Cloud Run).

    Cloud Run ajoute automatiquement un socket Unix via
    ``--add-cloudsql-instances``, utilisable dans le paramètre ``host``.

    Variables requises :
    - DB_USER
    - DB_PASSWORD
    - DB_NAME
    - INSTANCE_CONNECTION_NAME  (ex: projet:europe-west1:instance)
    """
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_name = os.getenv("DB_NAME")
    instance_connection = os.getenv("INSTANCE_CONNECTION_NAME")

    if all([db_user, db_password, db_name, instance_connection]):
        # Cloud SQL Auth Proxy expose le socket Unix sous /cloudsql/<instance>
        password_encoded = quote_plus(db_password)  # type: ignore[arg-type]
        return (
            f"postgresql+psycopg://{db_user}:{password_encoded}"
            f"@/{db_name}"
            f"?host=/cloudsql/{instance_connection}"
        )
    return None


@lru_cache(maxsize=1)
def get_database_url() -> str:
    """
    Retourne l'URL de connexion SQLAlchemy.

    Priorité :
    1. Variable d'env ``DATABASE_URL`` (connexion complète, ex. CI ou dev
       avec Postgres local).
    2. Construction automatique depuis les variables Cloud SQL individuelles
       (``DB_USER``, ``DB_PASSWORD``, ``DB_NAME``,
       ``INSTANCE_CONNECTION_NAME``).
    3. Fallback SQLite pour le développement local.
    """
    # --- Priorité 1 : URL complète ---
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    # --- Priorité 2 : Cloud SQL via variables individuelles ---
    cloud_url = _build_cloudsql_url()
    if cloud_url:
        return cloud_url

    # --- Priorité 3 : SQLite dev local ---
    return "sqlite:///./llm_task_manager.db"


def is_sqlite() -> bool:
    """Retourne True si la DB courante est SQLite (dev local)."""
    return get_database_url().startswith("sqlite")


