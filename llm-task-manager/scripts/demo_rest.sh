#!/bin/bash
# =============================================================================
# Script de démo REST — LLM Task Manager
#
# SCÉNARIO RÉALISTE basé sur ARCHITECTURE.md (Personas Henri & Marie)
#
# Contexte :
#   Henri est PO de "FieldConnect", une app de coordination terrain en usine.
#   Il reçoit des observations terrain et doit les transformer en backlog.
#   Marie est PM de la suite applicative et a besoin de synthèses sprint.
#
# Ce script déroule :
#   Partie 1 — Henri structure le backlog à partir d'observations terrain
#   Partie 2 — Henri gère un sprint (affectation, workflow, règles métier)
#   Partie 3 — Marie génère la documentation et la rétrospective
#
# Usage :
#   ./scripts/demo_rest.sh [BASE_URL] [API_KEY]
# =============================================================================
set -euo pipefail

BASE="${1:-https://llm-task-manager-714138868820.europe-west1.run.app}"
API_KEY="${2:-${API_KEY:-changeme}}"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

step=0
pause() {
    step=$((step + 1))
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  ${step}. $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    if [ -n "${2:-}" ]; then
        echo -e "  ${DIM}$2${NC}"
    fi
    echo ""
    read -p "  [Entrée] "
}

call() {
    local method=$1 path=$2 data=${3:-}
    echo -e "  ${YELLOW}${method} ${path}${NC}"
    if [ -n "$data" ]; then
        echo -e "  ${DIM}$(echo "$data" | python3 -m json.tool 2>/dev/null || echo "$data")${NC}"
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
        echo -e "  ${GREEN}✓ HTTP ${http_code}${NC}"
    else
        echo -e "  ${RED}✗ HTTP ${http_code} (erreur attendue)${NC}"
    fi
    echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
    echo ""
    LAST_RESPONSE="$body"
}

extract_id() {
    echo "$LAST_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null
}

# ─────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       LLM Task Manager — Démo REST (20 min)                 ║${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║  Persona 1 : Henri — Product Owner industriel               ║${NC}"
echo -e "${GREEN}║  Persona 2 : Marie — Product Manager suite applicative      ║${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║  Contexte : App \"FieldConnect\" — coordination terrain usine  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${DIM}URL     : ${BASE}${NC}"
echo -e "  ${DIM}API Key : ${API_KEY:0:12}...${NC}"

# ═══════════════════════════════════════════════════════════════
# PARTIE 1 — Henri structure le backlog depuis les observations terrain
# ═══════════════════════════════════════════════════════════════

echo ""
echo -e "${BOLD}══════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  PARTIE 1 — Henri structure le backlog terrain          ${NC}"
echo -e "${BOLD}══════════════════════════════════════════════════════════${NC}"

pause "Health Check — Vérification que le service Cloud Run est opérationnel"
call GET /health

pause "Henri crée le projet FieldConnect" \
    "Henri gère FieldConnect, une app de coordination terrain en usine (tournées, alertes maintenance, shifts)."
call POST /v1/projects '{"name": "FieldConnect", "description": "Application de coordination terrain pour usines — gestion des tournées opérateurs, alertes maintenance et rapports de shift."}'
PROJECT_ID=$(extract_id)
echo -e "  ${GREEN}→ Projet créé : ${PROJECT_ID}${NC}"

pause "Henri transforme ses observations terrain en epics" \
    "Après une semaine en usine, Henri a identifié 3 axes d'amélioration majeurs."

call POST /v1/epics '{"project_id": "'$PROJECT_ID'", "title": "Alertes maintenance prédictive"}'
EPIC_MAINT_ID=$(extract_id)
echo -e "  ${GREEN}→ Epic maintenance : ${EPIC_MAINT_ID}${NC}"

call POST /v1/epics '{"project_id": "'$PROJECT_ID'", "title": "Gestion des shifts et rotations"}'
EPIC_SHIFT_ID=$(extract_id)
echo -e "  ${GREEN}→ Epic shifts : ${EPIC_SHIFT_ID}${NC}"

call POST /v1/epics '{"project_id": "'$PROJECT_ID'", "title": "Dashboard temps réel usine"}'
EPIC_DASH_ID=$(extract_id)
echo -e "  ${GREEN}→ Epic dashboard : ${EPIC_DASH_ID}${NC}"

pause "Henri crée les stories depuis les retours terrain (estimation Fibonacci)" \
    "Les opérateurs ont remonté des problèmes concrets. Henri estime en story points (0,1,2,3,5,8,13)."

echo -e "  ${DIM}--- Epic : Alertes maintenance prédictive ---${NC}"
call POST /v1/stories '{"project_id": "'$PROJECT_ID'", "epic_id": "'$EPIC_MAINT_ID'", "title": "Notification push quand un capteur dépasse le seuil critique", "story_points": 8, "priority": "critical", "assignee": "henri"}'
STORY_NOTIF_ID=$(extract_id)

call POST /v1/stories '{"project_id": "'$PROJECT_ID'", "epic_id": "'$EPIC_MAINT_ID'", "title": "Historique des alertes maintenance sur 30 jours", "story_points": 5, "priority": "high", "assignee": "lucas"}'
STORY_HISTO_ID=$(extract_id)

echo -e "  ${DIM}--- Epic : Gestion des shifts ---${NC}"
call POST /v1/stories '{"project_id": "'$PROJECT_ID'", "epic_id": "'$EPIC_SHIFT_ID'", "title": "Planning de rotation des opérateurs (vue semaine)", "story_points": 13, "priority": "high", "assignee": "sarah"}'
STORY_PLANNING_ID=$(extract_id)

call POST /v1/stories '{"project_id": "'$PROJECT_ID'", "epic_id": "'$EPIC_SHIFT_ID'", "title": "Rapport de passation de shift (formulaire mobile)", "story_points": 3, "priority": "medium", "assignee": "lucas"}'
STORY_RAPPORT_ID=$(extract_id)

echo -e "  ${DIM}--- Epic : Dashboard ---${NC}"
call POST /v1/stories '{"project_id": "'$PROJECT_ID'", "epic_id": "'$EPIC_DASH_ID'", "title": "Widget temps réel — taux de disponibilité machines", "story_points": 5, "priority": "medium", "assignee": "henri"}'
STORY_WIDGET_ID=$(extract_id)

# ─── ERREUR MÉTIER 1 : story points hors Fibonacci ───
pause "RÈGLE MÉTIER — Story points hors Fibonacci" \
    "Henri essaie de créer une story avec 7 points (non autorisé : seulement 0,1,2,3,5,8,13)."
call POST /v1/stories '{"project_id": "'$PROJECT_ID'", "epic_id": "'$EPIC_DASH_ID'", "title": "Story mal estimée", "story_points": 7, "priority": "low"}'

pause "Henri filtre les stories critiques et celles assignées à Lucas" \
    "Henri veut prioriser : quelles stories sont critiques ? Que fait Lucas ?"
call GET "/v1/stories?priority=critical"
call GET "/v1/stories?assignee=lucas"

pause "Henri recherche les stories liées à la maintenance" \
    "Recherche par mot-clé dans les titres."
call GET "/v1/stories/search?q=maintenance"

# ═══════════════════════════════════════════════════════════════
# PARTIE 2 — Henri gère le sprint (workflow + règles métier)
# ═══════════════════════════════════════════════════════════════

echo ""
echo -e "${BOLD}══════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  PARTIE 2 — Henri gère le Sprint 1                      ${NC}"
echo -e "${BOLD}══════════════════════════════════════════════════════════${NC}"

pause "Henri crée le Sprint 1 — Alertes maintenance MVP" \
    "Le sprint couvre 2 semaines, focalisé sur les alertes maintenance (besoin terrain urgent)."
call POST /v1/sprints '{"project_id": "'$PROJECT_ID'", "name": "Sprint 1 — Alertes maintenance MVP", "start_date": "2026-02-17", "end_date": "2026-03-02"}'
SPRINT_ID=$(extract_id)
echo -e "  ${GREEN}→ Sprint créé : ${SPRINT_ID}${NC}"

pause "Henri affecte les 2 stories maintenance au sprint" \
    "Seules les stories de l'epic maintenance entrent dans ce sprint."
call POST "/v1/sprints/${SPRINT_ID}/stories/${STORY_NOTIF_ID}"
call POST "/v1/sprints/${SPRINT_ID}/stories/${STORY_HISTO_ID}"

pause "Henri démarre le sprint"
call POST "/v1/sprints/${SPRINT_ID}/start"

pause "Workflow — Henri fait avancer la story 'Notifications capteurs'" \
    "Workflow strict : backlog → todo → in_progress → in_review → done (pas de saut)."

echo -e "  ${YELLOW}backlog → todo${NC} (Henri prend la story en charge)"
call PATCH "/v1/stories/${STORY_NOTIF_ID}" '{"status": "todo"}'

echo -e "  ${YELLOW}todo → in_progress${NC} (développement en cours)"
call PATCH "/v1/stories/${STORY_NOTIF_ID}" '{"status": "in_progress"}'

echo -e "  ${YELLOW}in_progress → in_review${NC} (code review par Lucas)"
call PATCH "/v1/stories/${STORY_NOTIF_ID}" '{"status": "in_review"}'

echo -e "  ${YELLOW}in_review → done${NC} (validé et mergé)"
call PATCH "/v1/stories/${STORY_NOTIF_ID}" '{"status": "done"}'

# ─── ERREUR MÉTIER 2 : retour depuis done ───
pause "RÈGLE MÉTIER — Pas de retour depuis done" \
    "Henri essaie de remettre la story en in_progress (interdit : done est un état final)."
call PATCH "/v1/stories/${STORY_NOTIF_ID}" '{"status": "in_progress"}'

# ─── ERREUR MÉTIER 3 : saut de statut ───
pause "RÈGLE MÉTIER — Pas de saut de statut" \
    "Henri essaie de passer la 2e story directement de backlog à done (interdit)."
call PATCH "/v1/stories/${STORY_HISTO_ID}" '{"status": "done"}'

# ─── ERREUR MÉTIER 4 : clôture sprint impossible ───
pause "RÈGLE MÉTIER — Sprint non clôturable" \
    "Henri tente de clôturer le sprint mais 'Historique alertes' est encore en backlog."
call POST "/v1/sprints/${SPRINT_ID}/close"

pause "Henri termine la 2e story et clôture le sprint" \
    "Lucas finit l'historique des alertes → le sprint peut être clôturé."

call PATCH "/v1/stories/${STORY_HISTO_ID}" '{"status": "todo"}'
call PATCH "/v1/stories/${STORY_HISTO_ID}" '{"status": "in_progress"}'
call PATCH "/v1/stories/${STORY_HISTO_ID}" '{"status": "in_review"}'
call PATCH "/v1/stories/${STORY_HISTO_ID}" '{"status": "done"}'

echo -e "  ${YELLOW}Toutes les stories sont done → clôture du sprint${NC}"
call POST "/v1/sprints/${SPRINT_ID}/close"

# ═══════════════════════════════════════════════════════════════
# PARTIE 3 — Marie : documentation, rétrospective, synthèse
# ═══════════════════════════════════════════════════════════════

echo ""
echo -e "${BOLD}══════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  PARTIE 3 — Marie documente et analyse                  ${NC}"
echo -e "${BOLD}══════════════════════════════════════════════════════════${NC}"

pause "Henri et Lucas ajoutent des commentaires sur les stories livrées" \
    "Traçabilité : chaque story terminée est commentée par le dev et le reviewer."
call POST /v1/comments '{"project_id": "'$PROJECT_ID'", "target_type": "story", "target_id": "'$STORY_NOTIF_ID'", "content": "Intégration capteurs OK. Seuils configurables par zone usine. Tests E2E passés sur env staging."}'
call POST /v1/comments '{"project_id": "'$PROJECT_ID'", "target_type": "story", "target_id": "'$STORY_HISTO_ID'", "content": "Historique 30j implémenté avec pagination. Export CSV disponible. Review par Sarah."}'
call POST /v1/comments '{"project_id": "'$PROJECT_ID'", "target_type": "epic", "target_id": "'$EPIC_MAINT_ID'", "content": "Sprint 1 livré. MVP alertes opérationnel. Retours terrain attendus semaine prochaine."}'

pause "Marie rédige la rétrospective du Sprint 1" \
    "Marie utilise le template Sprint Retrospective pour structurer l'analyse."
call POST /v1/documents '{"project_id": "'$PROJECT_ID'", "title": "Rétrospective Sprint 1 — Alertes maintenance MVP", "content": "## Ce qui a bien fonctionné\n\n- Livraison dans les temps des 2 stories maintenance\n- Collaboration Henri/Lucas efficace sur les capteurs\n- Tests terrain validés dès le mercredi (J+8)\n\n## Ce qui peut être amélioré\n\n- Estimation de la story notifications (8pts) légèrement sous-évaluée\n- Manque de specs sur les seuils par zone → à documenter\n- Besoin d'un env de test avec données capteurs réalistes\n\n## Actions\n\n- [ ] Créer un jeu de données capteurs pour l'env de test\n- [ ] Documenter les seuils critiques par type de machine\n- [ ] Planifier une session terrain pour le Sprint 2"}'

pause "Marie crée un Problem Statement pour le Sprint 2" \
    "Marie prépare le cadrage du prochain sprint avec un document structuré."
call POST /v1/documents '{"project_id": "'$PROJECT_ID'", "title": "Problem Statement — Gestion des shifts", "content": "## Problème\n\nLes opérateurs n'\''ont pas de visibilité sur leur planning de rotation. Les passations de shift se font à l'\''oral, ce qui engendre des pertes d'\''information (pannes non signalées, consignes oubliées).\n\n## Impact\n\n- 15% des incidents post-shift liés à un défaut de passation\n- Temps moyen de passation : 25 min (objectif : 10 min)\n- 3 incidents critiques en janvier liés à une mauvaise rotation\n\n## Solution envisagée\n\n- Formulaire mobile de passation (structuré, obligatoire)\n- Planning de rotation visible sur l'\''app (vue semaine)\n- Notification push au changement de shift\n\n## Critères de succès\n\n- Temps de passation < 10 min\n- 0 incident lié à un défaut d'\''info post-shift\n- Adoption > 80% des opérateurs en 2 sprints"}'

pause "Marie recherche tous les documents du projet"
call GET "/v1/documents?project_id=${PROJECT_ID}"

pause "Marie consulte l'état global — tous les sprints et stories" \
    "Vue d'ensemble pour le comité produit hebdomadaire."
call GET "/v1/sprints?project_id=${PROJECT_ID}"
call GET "/v1/stories?project_id=${PROJECT_ID}"

# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    DÉMO TERMINÉE                             ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BOLD}Personas démontrés :${NC}"
echo "  👤 Henri (PO) — Structuration backlog, gestion sprint, workflow"
echo "  👤 Marie (PM) — Rétrospective, Problem Statement, vue d'ensemble"
echo ""
echo -e "${BOLD}Règles métier démontrées :${NC}"
echo "  ✓ Story points Fibonacci (rejet de 7 → seuls 0,1,2,3,5,8,13)"
echo "  ✓ Workflow strict backlog → todo → in_progress → in_review → done"
echo "  ✓ Pas de retour depuis done"
echo "  ✓ Pas de saut de statut (backlog → done interdit)"
echo "  ✓ Sprint non clôturable si stories ≠ done"
echo "  ✓ Affectation stories ↔ sprint"
echo ""
echo -e "${BOLD}Entités couvertes (6/6) :${NC}"
echo "  ✓ Projet    ✓ Epic       ✓ Story"
echo "  ✓ Sprint    ✓ Commentaire ✓ Document"
echo ""
echo -e "${BOLD}Fonctionnalités REST couvertes :${NC}"
echo "  ✓ CRUD complet    ✓ Filtrage (priorité, assignee)"
echo "  ✓ Recherche        ✓ Workflow statuts"
echo "  ✓ Gestion sprint   ✓ Erreurs métier (400/409/422)"
echo ""
