#!/bin/bash
# =============================================================================
# Script de démarrage du container — LLM Task Manager
#
# 1. Exécute les migrations Alembic (si PostgreSQL / Cloud SQL)
# 2. Lance le serveur Uvicorn
#
# Cf. ARCHITECTURE.md § Pipeline CI/CD
# =============================================================================
set -e

echo "=== LLM Task Manager — Démarrage ==="

# --- Migrations Alembic (uniquement si une vraie DB est configurée) ---
if [ -n "$DATABASE_URL" ] || [ -n "$INSTANCE_CONNECTION_NAME" ]; then
    echo ">>> Exécution des migrations Alembic..."
    alembic upgrade head
    echo ">>> Migrations terminées."
else
    echo ">>> Mode dev local (SQLite) — migrations ignorées (init_db au démarrage)."
fi

# --- Lancement du serveur ---
echo ">>> Démarrage Uvicorn sur le port ${PORT:-8080}..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8080}" \
    --workers 1 \
    --log-level info
