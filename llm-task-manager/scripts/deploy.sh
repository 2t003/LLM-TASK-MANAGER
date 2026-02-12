#!/bin/bash
# =============================================================================
# Script de déploiement manuel — LLM Task Manager → Cloud Run
#
# Usage :
#   ./scripts/deploy.sh
#
# Prérequis :
#   1. gcloud CLI installé et authentifié (gcloud auth login)
#   2. Projet GCP configuré (gcloud config set project <PROJECT_ID>)
#   3. APIs activées : Cloud Run, Cloud Build, Artifact Registry, Cloud SQL
#   4. Instance Cloud SQL PostgreSQL créée
#   5. Variables d'environnement définies (voir .env.example)
#
# Ce script :
#   1. Build l'image Docker
#   2. Push vers Artifact Registry
#   3. Déploie sur Cloud Run (europe-west1) avec connexion Cloud SQL
#
# Cf. ARCHITECTURE.md § Pipeline CI/CD & Cloud Run
# =============================================================================
set -euo pipefail

# ---- Configuration (modifier selon votre projet GCP) ----
PROJECT_ID="${GCP_PROJECT_ID:?'Variable GCP_PROJECT_ID requise'}"
REGION="${GCP_REGION:-europe-west1}"
SERVICE_NAME="${SERVICE_NAME:-llm-task-manager}"
REPOSITORY="${ARTIFACT_REPO:-llm-task-manager}"
IMAGE_NAME="${IMAGE_NAME:-llm-task-manager}"

# Cloud SQL
INSTANCE_CONNECTION_NAME="${INSTANCE_CONNECTION_NAME:?'Variable INSTANCE_CONNECTION_NAME requise (ex: project:region:instance)'}"
DB_USER="${DB_USER:-postgres}"
DB_NAME="${DB_NAME:-llm_task_manager}"
DB_PASSWORD_SECRET="${DB_PASSWORD_SECRET:-llm-task-manager-db-password}"
API_KEY_SECRET="${API_KEY_SECRET:-llm-task-manager-api-key}"

# Image complète
IMAGE_TAG="$(date +%Y%m%d-%H%M%S)"
FULL_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}"

echo "============================================="
echo " LLM Task Manager — Déploiement Cloud Run"
echo "============================================="
echo ""
echo "  Projet GCP       : ${PROJECT_ID}"
echo "  Région            : ${REGION}"
echo "  Service           : ${SERVICE_NAME}"
echo "  Image             : ${FULL_IMAGE}:${IMAGE_TAG}"
echo "  Cloud SQL         : ${INSTANCE_CONNECTION_NAME}"
echo "  DB                : ${DB_USER}@${DB_NAME}"
echo ""

# ---- Étape 0 : Vérifications préalables ----
echo ">>> Vérification du projet GCP..."
gcloud config set project "${PROJECT_ID}" --quiet

# Créer le repository Artifact Registry s'il n'existe pas
echo ">>> Vérification du repository Artifact Registry..."
if ! gcloud artifacts repositories describe "${REPOSITORY}" \
    --location="${REGION}" --format="value(name)" 2>/dev/null; then
    echo ">>> Création du repository Artifact Registry..."
    gcloud artifacts repositories create "${REPOSITORY}" \
        --repository-format=docker \
        --location="${REGION}" \
        --description="Images Docker LLM Task Manager"
fi

# Configurer Docker pour Artifact Registry
echo ">>> Configuration Docker pour Artifact Registry..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# ---- Étape 1 : Build de l'image Docker ----
echo ""
echo ">>> Build de l'image Docker..."
docker build \
    -t "${FULL_IMAGE}:${IMAGE_TAG}" \
    -t "${FULL_IMAGE}:latest" \
    .

# ---- Étape 2 : Push vers Artifact Registry ----
echo ""
echo ">>> Push vers Artifact Registry..."
docker push "${FULL_IMAGE}:${IMAGE_TAG}"
docker push "${FULL_IMAGE}:latest"

# ---- Étape 3 : Déploiement Cloud Run ----
echo ""
echo ">>> Déploiement sur Cloud Run (${REGION})..."
gcloud run deploy "${SERVICE_NAME}" \
    --image "${FULL_IMAGE}:${IMAGE_TAG}" \
    --region "${REGION}" \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --min-instances 0 \
    --max-instances 5 \
    --concurrency 20 \
    --cpu 1 \
    --memory 512Mi \
    --add-cloudsql-instances "${INSTANCE_CONNECTION_NAME}" \
    --set-env-vars "PYTHONUNBUFFERED=1,DB_USER=${DB_USER},DB_NAME=${DB_NAME},INSTANCE_CONNECTION_NAME=${INSTANCE_CONNECTION_NAME}" \
    --update-secrets "DB_PASSWORD=${DB_PASSWORD_SECRET}:latest,API_KEY=${API_KEY_SECRET}:latest"

# ---- Étape 4 : Vérification post-deploy ----
echo ""
echo ">>> Récupération de l'URL du service..."
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --region="${REGION}" \
    --format='value(status.url)')

echo "   URL du service : ${SERVICE_URL}"
echo ""
echo ">>> Vérification /health..."
sleep 5  # Attendre le démarrage

for i in 1 2 3; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${SERVICE_URL}/health")
    echo "   Tentative ${i}: /health → ${STATUS}"
    if [ "${STATUS}" = "200" ]; then
        echo ""
        echo "============================================="
        echo " DÉPLOIEMENT RÉUSSI"
        echo "============================================="
        echo ""
        echo "  URL service  : ${SERVICE_URL}"
        echo "  Health       : ${SERVICE_URL}/health"
        echo "  API docs     : ${SERVICE_URL}/docs"
        echo "  API v1       : ${SERVICE_URL}/v1/"
        echo ""
        exit 0
    fi
    sleep 5
done

echo ""
echo "ERREUR : /health n'a pas renvoyé 200 après 3 tentatives."
echo "Consultez les logs : gcloud run logs read --service=${SERVICE_NAME} --region=${REGION}"
exit 1
