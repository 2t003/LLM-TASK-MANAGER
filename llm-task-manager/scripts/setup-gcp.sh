#!/bin/bash
# =============================================================================
# Script de setup GCP — LLM Task Manager
#
# Usage :
#   ./scripts/setup-gcp.sh
#
# Ce script configure l'infrastructure GCP nécessaire :
#   1. Active les APIs requises
#   2. Crée l'instance Cloud SQL (PostgreSQL)
#   3. Crée la base de données
#   4. Crée les secrets dans Secret Manager
#   5. Crée le repository Artifact Registry
#
# Prérequis :
#   - gcloud CLI installé et authentifié
#   - Projet GCP existant
#   - Variables d'environnement du .env (ou valeurs par défaut)
#
# Cf. ARCHITECTURE.md § Services GCP utilisés
# =============================================================================
set -euo pipefail

# ---- Configuration ----
PROJECT_ID="${GCP_PROJECT_ID:?'Variable GCP_PROJECT_ID requise'}"
REGION="${GCP_REGION:-europe-west1}"
INSTANCE_NAME="${CLOUD_SQL_INSTANCE:-llm-task-db}"
DB_NAME="${DB_NAME:-llm_task_manager}"
DB_USER="${DB_USER:-postgres}"

echo "============================================="
echo " LLM Task Manager — Setup GCP"
echo "============================================="
echo ""
echo "  Projet   : ${PROJECT_ID}"
echo "  Région   : ${REGION}"
echo "  Instance : ${INSTANCE_NAME}"
echo "  DB       : ${DB_NAME}"
echo ""

# ---- Étape 1 : Activer les APIs ----
echo ">>> Activation des APIs GCP..."
gcloud services enable \
    run.googleapis.com \
    sqladmin.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    --project="${PROJECT_ID}"

echo "   APIs activées."

# ---- Étape 2 : Créer l'instance Cloud SQL ----
echo ""
echo ">>> Création de l'instance Cloud SQL (peut prendre ~5 min)..."
if gcloud sql instances describe "${INSTANCE_NAME}" \
    --project="${PROJECT_ID}" --format="value(name)" 2>/dev/null; then
    echo "   Instance ${INSTANCE_NAME} existe déjà."
else
    gcloud sql instances create "${INSTANCE_NAME}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --database-version=POSTGRES_15 \
        --tier=db-f1-micro \
        --storage-size=10GB \
        --storage-auto-increase \
        --no-assign-ip \
        --enable-google-private-path
    echo "   Instance ${INSTANCE_NAME} créée."
fi

# ---- Étape 3 : Créer la base de données ----
echo ""
echo ">>> Création de la base de données ${DB_NAME}..."
if gcloud sql databases describe "${DB_NAME}" \
    --instance="${INSTANCE_NAME}" \
    --project="${PROJECT_ID}" --format="value(name)" 2>/dev/null; then
    echo "   Base ${DB_NAME} existe déjà."
else
    gcloud sql databases create "${DB_NAME}" \
        --instance="${INSTANCE_NAME}" \
        --project="${PROJECT_ID}"
    echo "   Base ${DB_NAME} créée."
fi

# ---- Étape 4 : Définir le mot de passe du user postgres ----
echo ""
echo ">>> Définition du mot de passe pour l'utilisateur ${DB_USER}..."
read -s -p "   Entrez le mot de passe pour ${DB_USER}: " DB_PASSWORD
echo ""
gcloud sql users set-password "${DB_USER}" \
    --instance="${INSTANCE_NAME}" \
    --project="${PROJECT_ID}" \
    --password="${DB_PASSWORD}"
echo "   Mot de passe défini."

# ---- Étape 5 : Stocker les secrets dans Secret Manager ----
echo ""
echo ">>> Stockage des secrets dans Secret Manager..."

# DB Password
echo -n "${DB_PASSWORD}" | gcloud secrets create "llm-task-manager-db-password" \
    --data-file=- \
    --project="${PROJECT_ID}" 2>/dev/null || \
echo -n "${DB_PASSWORD}" | gcloud secrets versions add "llm-task-manager-db-password" \
    --data-file=- \
    --project="${PROJECT_ID}"
echo "   Secret DB_PASSWORD stocké."

# API Key (génération automatique)
API_KEY=$(openssl rand -hex 32)
echo -n "${API_KEY}" | gcloud secrets create "llm-task-manager-api-key" \
    --data-file=- \
    --project="${PROJECT_ID}" 2>/dev/null || \
echo -n "${API_KEY}" | gcloud secrets versions add "llm-task-manager-api-key" \
    --data-file=- \
    --project="${PROJECT_ID}"
echo "   Secret API_KEY stocké."
echo "   API Key générée : ${API_KEY}"
echo "   (Conservez cette clé précieusement !)"

# ---- Étape 6 : Créer le repository Artifact Registry ----
echo ""
echo ">>> Création du repository Artifact Registry..."
if gcloud artifacts repositories describe "llm-task-manager" \
    --location="${REGION}" \
    --project="${PROJECT_ID}" --format="value(name)" 2>/dev/null; then
    echo "   Repository existe déjà."
else
    gcloud artifacts repositories create "llm-task-manager" \
        --repository-format=docker \
        --location="${REGION}" \
        --project="${PROJECT_ID}" \
        --description="Images Docker LLM Task Manager"
    echo "   Repository créé."
fi

# ---- Étape 7 : Donner accès aux secrets au service account Cloud Run ----
echo ""
echo ">>> Configuration IAM pour Cloud Run..."
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")
SA_EMAIL="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

for SECRET in "llm-task-manager-db-password" "llm-task-manager-api-key"; do
    gcloud secrets add-iam-policy-binding "${SECRET}" \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="roles/secretmanager.secretAccessor" \
        --project="${PROJECT_ID}" --quiet
done
echo "   Service account Cloud Run autorisé à lire les secrets."

# ---- Résumé ----
INSTANCE_CONNECTION="${PROJECT_ID}:${REGION}:${INSTANCE_NAME}"
echo ""
echo "============================================="
echo " SETUP TERMINÉ"
echo "============================================="
echo ""
echo "  Instance Cloud SQL    : ${INSTANCE_NAME}"
echo "  Connection name       : ${INSTANCE_CONNECTION}"
echo "  Base de données       : ${DB_NAME}"
echo "  Utilisateur           : ${DB_USER}"
echo "  API Key               : ${API_KEY}"
echo ""
echo "  Pour déployer :"
echo "    export GCP_PROJECT_ID=${PROJECT_ID}"
echo "    export INSTANCE_CONNECTION_NAME=${INSTANCE_CONNECTION}"
echo "    ./scripts/deploy.sh"
echo ""
