# =============================================================================
# Dockerfile — LLM Task Manager
#
# Image de production pour Cloud Run (europe-west1).
# Cf. ARCHITECTURE.md § Pipeline CI/CD & Cloud Run
# =============================================================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copier les fichiers de dépendances d'abord (cache Docker)
COPY pyproject.toml README.md ./

# Copier le code source
COPY app ./app

# Copier la config Alembic (migrations DB)
COPY alembic.ini ./
COPY alembic ./alembic

# Installer les dépendances
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Port par défaut Cloud Run
ENV PORT=8080

EXPOSE 8080

# Démarrage direct Uvicorn — init_db() dans le lifespan FastAPI crée les tables
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--log-level", "info"]
