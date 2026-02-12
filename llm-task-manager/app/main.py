from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan handler : initialise le schéma DB au démarrage.

    En production, les migrations Alembic gèrent le schéma.
    Ce fallback garantit que les tables existent en dev local / SQLite.
    """
    from app.db import init_db

    init_db()
    yield


def create_app() -> FastAPI:
    """
    Crée et configure l'application FastAPI principale.
    """
    app = FastAPI(
        title="LLM Task Manager",
        version="0.1.0",
        description="Gestionnaire de tâches pour humains et LLMs (REST + MCP).",
        lifespan=lifespan,
    )

    @app.get("/health", tags=["health"])
    async def health() -> dict:
        """
        Endpoint de santé utilisé par Cloud Run et le monitoring.
        """
        return {"status": "ok"}

    # Point d'extension : inclure les routers métier
    app.include_router(api_router, prefix="/v1")

    return app


app = create_app()

