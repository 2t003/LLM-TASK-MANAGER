# Démo MCP — LLM Task Manager

## Contexte (identique à la démo REST)

- **Henri** — PO de *FieldConnect*, une app de coordination terrain en usine
- **Marie** — PM de la suite applicative, vision stratégique

Le serveur MCP expose 25 tools qui appellent la même logique métier que l'API REST.

---

## Prérequis

Le fichier `.cursor/mcp.json` est configuré. Redémarrer Cursor si nécessaire.
Vérifier dans **Settings → MCP** que `llm-task-manager` apparaît avec un point vert.

---

## Scénario de démo — Prompts à dérouler

### PARTIE 1 — Henri structure le backlog terrain

---

**Prompt 1** — Créer le projet

> "Crée un projet appelé 'FieldConnect' avec la description 'Application de coordination terrain pour usines — gestion des tournées opérateurs, alertes maintenance et rapports de shift'."

Tool : `create_project`

---

**Prompt 2** — Créer les epics depuis les observations terrain

> "Dans le projet FieldConnect, crée trois epics :
> 1. 'Alertes maintenance prédictive'
> 2. 'Gestion des shifts et rotations'
> 3. 'Dashboard temps réel usine'"

Tool : `create_epic` (×3)

---

**Prompt 3** — Créer les stories avec estimation terrain

> "Dans l'epic 'Alertes maintenance prédictive', crée ces stories :
> - 'Notification push quand un capteur dépasse le seuil critique' — 8 points, priorité critical, assignée à Henri
> - 'Historique des alertes maintenance sur 30 jours' — 5 points, priorité high, assignée à Lucas
>
> Dans l'epic 'Gestion des shifts', crée :
> - 'Planning de rotation des opérateurs (vue semaine)' — 13 points, priorité high, assignée à Sarah
> - 'Rapport de passation de shift (formulaire mobile)' — 3 points, priorité medium, assignée à Lucas"

Tool : `create_story` (×4)

---

**Prompt 4** — ERREUR : estimation invalide

> "Crée une story 'Test capteur zone B' avec 7 story points."

Résultat attendu : **erreur** — 7 n'est pas dans la suite Fibonacci (0,1,2,3,5,8,13).

---

**Prompt 5** — Recherche et filtrage

> "Quelles sont les stories critiques ? Et qu'est-ce qui est assigné à Lucas ?"

Tools : `list_stories` avec filtres `priority=critical`, `assignee=lucas`

---

### PARTIE 2 — Henri gère le Sprint 1

---

**Prompt 6** — Sprint + affectation

> "Crée un sprint 'Sprint 1 — Alertes maintenance MVP' du 17 février au 2 mars 2026. Affecte-y les deux stories de l'epic maintenance."

Tools : `create_sprint`, `add_story_to_sprint` (×2)

---

**Prompt 7** — Démarrage

> "Démarre le Sprint 1."

Tool : `start_sprint`

---

**Prompt 8** — Workflow complet

> "Fais avancer la story 'Notification push capteurs' dans le workflow : passe-la en todo, puis in_progress, puis in_review, et enfin done."

Tool : `update_story` (×4 transitions)
Point à montrer : le workflow strict est respecté étape par étape.

---

**Prompt 9** — ERREUR : retour depuis done

> "Remets la story 'Notification push capteurs' en in_progress."

Résultat attendu : **erreur** — done est un état final, pas de retour possible.

---

**Prompt 10** — ERREUR : clôture impossible

> "Clôture le Sprint 1."

Résultat attendu : **erreur** — la story 'Historique alertes' n'est pas done.

---

**Prompt 11** — Terminer et clôturer

> "Fais passer 'Historique des alertes' jusqu'à done, puis clôture le sprint."

Tools : `update_story` (×4), `close_sprint`

---

### PARTIE 3 — Marie documente et analyse

---

**Prompt 12** — Commentaires

> "Ajoute un commentaire sur la story des notifications : 'Intégration capteurs OK. Seuils configurables par zone. Tests E2E passés en staging.'
> Et un commentaire sur l'epic maintenance : 'Sprint 1 livré. MVP alertes opérationnel. Retours terrain attendus la semaine prochaine.'"

Tools : `add_comment` (×2)

---

**Prompt 13** — Rétrospective

> "Crée un document 'Rétrospective Sprint 1 — Alertes maintenance MVP' avec :
> - Ce qui a bien fonctionné : livraison dans les temps, collab Henri/Lucas, tests terrain validés J+8
> - À améliorer : story notifications sous-estimée, manque de specs seuils par zone
> - Actions : jeu de données capteurs test, documenter seuils critiques, session terrain Sprint 2"

Tool : `create_document`

---

**Prompt 14** — Problem Statement Sprint 2

> "Crée un document 'Problem Statement — Gestion des shifts' expliquant le problème de passation de shift en usine : pas de visibilité sur les rotations, passation orale, 15% d'incidents post-shift liés à un défaut d'info. Solution proposée : formulaire mobile, planning visible, notifications."

Tool : `create_document`

---

**Prompt 15** — Vue d'ensemble

> "Liste tous les sprints et toutes les stories du projet FieldConnect avec leur statut."

Tools : `list_sprints`, `list_stories`

---

## Résumé des règles métier démontrées

| Règle | Prompt | Résultat |
|---|---|---|
| Story points Fibonacci | #4 : 7 points | Erreur |
| Workflow strict | #8 : backlog → done | OK étape par étape |
| Pas de retour depuis done | #9 : done → in_progress | Erreur |
| Sprint non clôturable | #10 : stories ≠ done | Erreur |
| Parité REST / MCP | Même scénario, mêmes résultats | OK |

## Points clés pour les questions du jury

1. **Parité REST / MCP** — les tools MCP appellent les mêmes services que l'API REST
2. **Défense en profondeur** — Pydantic → Auth → Service Layer → SQL constraints
3. **Persona-driven** — Henri structure le backlog, Marie analyse et documente
4. **Validation humaine** — le LLM propose, l'humain confirme (cf. ARCHITECTURE.md §3.3)
5. **Transport stdio** — pas d'exposition réseau, sécurité maximale pour le MCP local
