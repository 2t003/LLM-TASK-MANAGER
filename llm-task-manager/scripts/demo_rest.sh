#!/bin/bash
# =============================================================================
# Script de démo REST — LLM Task Manager
#
# Ce script déroule un scénario complet pour la démonstration de 20 min :
#   1. Création d'un projet
#   2. Création d'epics
#   3. Création de stories (avec story points Fibonacci)
#   4. Création d'un sprint + affectation de stories
#   5. Workflow de statuts (transitions valides)
#   6. Démonstration des règles métier (erreurs attendues)
#   7. Clôture de sprint
#   8. Commentaires et documents
#
# Usage :
#   ./scripts/demo_rest.sh [BASE_URL] [API_KEY]
#
# Exemple :
#   ./scripts/demo_rest.sh https://llm-task-manager-714138868820.europe-west1.run.app MA_CLE
# =============================================================================
set -euo pipefail

BASE="${1:-https://llm-task-manager-714138868820.europe-west1.run.app}"
API_KEY="${2:-${API_KEY:-changeme}}"

# Couleurs pour la lisibilité
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

step=0
pause() {
    step=$((step + 1))
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  Étape ${step} : $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    read -p "  [Entrée pour continuer] "
}

call() {
    local method=$1 path=$2 data=${3:-}
    echo -e "${YELLOW}  → ${method} ${path}${NC}"
    if [ -n "$data" ]; then
        echo -e "    Body: ${data}"
    fi
    echo ""
    local response
    if [ -n "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" "${BASE}${path}" \
            -H "Content-Type: application/json" \
            -H "X-API-Key: ${API_KEY}" \
            -d "$data")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "${BASE}${path}" \
            -H "X-API-Key: ${API_KEY}")
    fi

    local http_code body
    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        echo -e "  ${GREEN}✓ ${http_code}${NC}"
    else
        echo -e "  ${RED}✗ ${http_code}${NC}"
    fi
    echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
    echo ""

    # Exporter dans LAST_RESPONSE pour extraction d'ID
    LAST_RESPONSE="$body"
}

extract_id() {
    echo "$LAST_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null
}

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     LLM Task Manager — Démo REST (20 min)        ║${NC}"
echo -e "${GREEN}║     URL : ${BASE}${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════╝${NC}"

# ─── 0. Health check ───
pause "Health Check"
call GET /health

# ─── 1. Créer un projet ───
pause "Créer un projet"
call POST /v1/projects '{"name": "Plateforme E-commerce", "description": "Refonte complète de la plateforme e-commerce avec panier et paiement"}'
PROJECT_ID=$(extract_id)
echo -e "  ${GREEN}→ PROJECT_ID = ${PROJECT_ID}${NC}"

# ─── 2. Lister les projets ───
pause "Lister les projets"
call GET /v1/projects

# ─── 3. Créer des epics ───
pause "Créer des epics"

call POST /v1/epics '{"project_id": "'$PROJECT_ID'", "title": "Gestion du panier"}'
EPIC_CART_ID=$(extract_id)
echo -e "  ${GREEN}→ EPIC_CART_ID = ${EPIC_CART_ID}${NC}"

call POST /v1/epics '{"project_id": "'$PROJECT_ID'", "title": "Système de paiement"}'
EPIC_PAY_ID=$(extract_id)
echo -e "  ${GREEN}→ EPIC_PAY_ID = ${EPIC_PAY_ID}${NC}"

# ─── 4. Créer des stories avec story points Fibonacci ───
pause "Créer des stories (story points Fibonacci : 0,1,2,3,5,8,13)"

call POST /v1/stories '{"project_id": "'$PROJECT_ID'", "epic_id": "'$EPIC_CART_ID'", "title": "Ajouter un produit au panier", "story_points": 3, "priority": "high"}'
STORY_ADD_ID=$(extract_id)
echo -e "  ${GREEN}→ STORY_ADD = ${STORY_ADD_ID}${NC}"

call POST /v1/stories '{"project_id": "'$PROJECT_ID'", "epic_id": "'$EPIC_CART_ID'", "title": "Afficher le résumé du panier", "story_points": 5, "priority": "medium"}'
STORY_VIEW_ID=$(extract_id)
echo -e "  ${GREEN}→ STORY_VIEW = ${STORY_VIEW_ID}${NC}"

call POST /v1/stories '{"project_id": "'$PROJECT_ID'", "epic_id": "'$EPIC_PAY_ID'", "title": "Intégration Stripe", "story_points": 13, "priority": "critical", "assignee": "alice"}'
STORY_STRIPE_ID=$(extract_id)
echo -e "  ${GREEN}→ STORY_STRIPE = ${STORY_STRIPE_ID}${NC}"

# ─── 5. ERREUR : story points invalides ───
pause "RÈGLE MÉTIER — Story points hors Fibonacci (attendu : erreur 422/400)"
call POST /v1/stories '{"project_id": "'$PROJECT_ID'", "title": "Story invalide", "story_points": 4, "priority": "low"}'

# ─── 6. Filtrer les stories ───
pause "Filtrer les stories par priorité et assignee"
call GET "/v1/stories?priority=critical"
call GET "/v1/stories?assignee=alice"

# ─── 7. Rechercher les stories ───
pause "Rechercher par mot-clé"
call GET "/v1/stories/search?q=panier"

# ─── 8. Créer un sprint ───
pause "Créer un sprint"
call POST /v1/sprints '{"project_id": "'$PROJECT_ID'", "name": "Sprint 1 - MVP Panier", "start_date": "2026-02-17", "end_date": "2026-03-02"}'
SPRINT_ID=$(extract_id)
echo -e "  ${GREEN}→ SPRINT_ID = ${SPRINT_ID}${NC}"

# ─── 9. Affecter des stories au sprint ───
pause "Affecter des stories au sprint"
call POST "/v1/sprints/${SPRINT_ID}/stories/${STORY_ADD_ID}"
call POST "/v1/sprints/${SPRINT_ID}/stories/${STORY_VIEW_ID}"

# ─── 10. Démarrer le sprint ───
pause "Démarrer le sprint"
call POST "/v1/sprints/${SPRINT_ID}/start"

# ─── 11. Workflow de statuts (transitions valides) ───
pause "Workflow : backlog → todo → in_progress → in_review → done"

echo -e "  ${YELLOW}Story 'Ajouter produit' : backlog → todo${NC}"
call PATCH "/v1/stories/${STORY_ADD_ID}" '{"status": "todo"}'

echo -e "  ${YELLOW}Story 'Ajouter produit' : todo → in_progress${NC}"
call PATCH "/v1/stories/${STORY_ADD_ID}" '{"status": "in_progress"}'

echo -e "  ${YELLOW}Story 'Ajouter produit' : in_progress → in_review${NC}"
call PATCH "/v1/stories/${STORY_ADD_ID}" '{"status": "in_review"}'

echo -e "  ${YELLOW}Story 'Ajouter produit' : in_review → done${NC}"
call PATCH "/v1/stories/${STORY_ADD_ID}" '{"status": "done"}'

# ─── 12. ERREUR : transition illégale (done → in_progress) ───
pause "RÈGLE MÉTIER — Transition illégale : done → in_progress (attendu : erreur 400)"
call PATCH "/v1/stories/${STORY_ADD_ID}" '{"status": "in_progress"}'

# ─── 13. ERREUR : saut de statut (backlog → done) ───
pause "RÈGLE MÉTIER — Saut de statut : backlog → done (attendu : erreur 400)"
call PATCH "/v1/stories/${STORY_VIEW_ID}" '{"status": "done"}'

# ─── 14. ERREUR : clôture sprint avec stories non terminées ───
pause "RÈGLE MÉTIER — Clôture sprint impossible (stories pas toutes done)"
call POST "/v1/sprints/${SPRINT_ID}/close"

# ─── 15. Terminer la 2e story et clôturer le sprint ───
pause "Terminer la 2e story puis clôturer le sprint"

echo -e "  ${YELLOW}Story 'Résumé panier' : backlog → todo → in_progress → in_review → done${NC}"
call PATCH "/v1/stories/${STORY_VIEW_ID}" '{"status": "todo"}'
call PATCH "/v1/stories/${STORY_VIEW_ID}" '{"status": "in_progress"}'
call PATCH "/v1/stories/${STORY_VIEW_ID}" '{"status": "in_review"}'
call PATCH "/v1/stories/${STORY_VIEW_ID}" '{"status": "done"}'

echo -e "  ${YELLOW}Clôture du sprint (toutes les stories sont done)${NC}"
call POST "/v1/sprints/${SPRINT_ID}/close"

# ─── 16. Ajouter des commentaires ───
pause "Ajouter des commentaires"
call POST /v1/comments '{"project_id": "'$PROJECT_ID'", "target_type": "story", "target_id": "'$STORY_ADD_ID'", "content": "Implémentation terminée, tests OK."}'
call POST /v1/comments '{"project_id": "'$PROJECT_ID'", "target_type": "epic", "target_id": "'$EPIC_CART_ID'", "content": "Sprint 1 livré avec succès."}'

# ─── 17. Lister les commentaires ───
pause "Lister les commentaires d'une story"
call GET "/v1/comments?target_id=${STORY_ADD_ID}"

# ─── 18. Créer un document ───
pause "Créer un document de spécification"
call POST /v1/documents '{"project_id": "'$PROJECT_ID'", "title": "Spec technique - Panier", "content": "## Architecture\n\n- Service panier (microservice)\n- Cache Redis pour le panier temporaire\n- API REST pour le CRUD panier\n\n## Endpoints\n\n- POST /cart/items\n- DELETE /cart/items/:id\n- GET /cart/summary"}'

# ─── 19. Rechercher des documents ───
pause "Rechercher des documents"
call GET "/v1/documents/search?q=Panier"

# ─── Fin ───
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     DÉMO TERMINÉE — Tous les scénarios OK         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Résumé des règles métier démontrées :"
echo "  ✓ Story points Fibonacci (0,1,2,3,5,8,13)"
echo "  ✓ Workflow strict : backlog → todo → in_progress → in_review → done"
echo "  ✓ Pas de retour depuis done"
echo "  ✓ Pas de saut de statut"
echo "  ✓ Clôture sprint bloquée si stories ≠ done"
echo "  ✓ Affectation story ↔ sprint"
echo "  ✓ CRUD complet 6 entités"
echo "  ✓ Filtrage et recherche"
echo ""
