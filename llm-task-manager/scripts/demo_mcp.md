# Démo MCP — LLM Task Manager

## Prérequis

Le fichier `.cursor/mcp.json` est déjà configuré à la racine du projet.
Cursor détecte automatiquement le serveur MCP au redémarrage.

> **Vérification** : dans Cursor, aller dans Settings → MCP → le serveur `llm-task-manager` doit apparaître avec ses tools.

---

## Scénario de démo (10 min MCP)

Ouvrir une conversation avec l'agent Cursor et lui demander d'utiliser les tools MCP.
Voici les prompts à dérouler dans l'ordre :

---

### 1. Créer un projet

> **Prompt** : "Crée un projet appelé 'Application Mobile Banking' avec la description 'App mobile pour consultation de comptes et virements'."

**Tool attendu** : `create_project`
**Vérification** : un UUID de projet est retourné.

---

### 2. Créer des epics

> **Prompt** : "Dans ce projet, crée deux epics : 'Authentification' et 'Consultation de comptes'."

**Tool attendu** : `create_epic` (×2)

---

### 3. Créer des stories avec estimation

> **Prompt** : "Dans l'epic Authentification, crée les stories suivantes :
> - 'Login par email/password' (8 points, priorité high)
> - 'Login biométrique' (13 points, priorité critical, assignée à Bob)
> - 'Écran mot de passe oublié' (3 points, priorité medium)"

**Tool attendu** : `create_story` (×3)
**Point à montrer** : les story points respectent la suite Fibonacci (3, 8, 13).

---

### 4. Tester une règle métier (story points invalides)

> **Prompt** : "Crée une story 'Test invalide' avec 7 story points."

**Résultat attendu** : erreur — 7 n'est pas dans la suite Fibonacci (0,1,2,3,5,8,13).
**Point à montrer** : le LLM reçoit un message d'erreur clair et peut le relayer.

---

### 5. Rechercher des stories

> **Prompt** : "Recherche toutes les stories qui contiennent 'login'."

**Tool attendu** : `search_stories`

---

### 6. Créer un sprint et y affecter des stories

> **Prompt** : "Crée un sprint 'Sprint 1 - Auth' du 17 février au 2 mars 2026, puis affecte-y les stories Login email et Login biométrique."

**Tools attendus** : `create_sprint`, `add_story_to_sprint` (×2)

---

### 7. Démarrer le sprint

> **Prompt** : "Démarre le Sprint 1."

**Tool attendu** : `start_sprint`

---

### 8. Workflow de statuts

> **Prompt** : "Fais passer la story 'Login email' de backlog à todo, puis in_progress, puis in_review, et enfin done."

**Tool attendu** : `update_story` (×4 transitions)
**Point à montrer** : le workflow strict est respecté étape par étape.

---

### 9. Tester une transition interdite

> **Prompt** : "Remets la story 'Login email' en in_progress."

**Résultat attendu** : erreur — pas de retour depuis `done`.
**Point à montrer** : le serveur MCP renvoie un message métier explicite au LLM.

---

### 10. Tester la clôture de sprint (bloquée)

> **Prompt** : "Clôture le Sprint 1."

**Résultat attendu** : erreur — la story 'Login biométrique' n'est pas encore `done`.
**Point à montrer** : règle métier « toutes les stories doivent être done ».

---

### 11. Terminer et clôturer

> **Prompt** : "Fais passer 'Login biométrique' jusqu'à done, puis clôture le sprint."

**Tools attendus** : `update_story` (×4), `close_sprint`

---

### 12. Commenter et documenter

> **Prompt** : "Ajoute un commentaire sur la story Login email : 'Tests unitaires OK, PR mergée'. Puis crée un document 'Spec Auth' avec un résumé de l'architecture d'authentification."

**Tools attendus** : `add_comment`, `create_document`

---

### 13. Vue d'ensemble

> **Prompt** : "Liste tous les sprints du projet et toutes les stories avec leur statut."

**Tools attendus** : `list_sprints`, `list_stories`

---

## Règles métier démontrées via MCP

| Règle | Scénario | Résultat |
|---|---|---|
| Story points Fibonacci | Création avec 7 points | Erreur |
| Workflow strict | backlog → todo → ... → done | OK |
| Pas de retour depuis done | done → in_progress | Erreur |
| Clôture sprint bloquée | Sprint avec stories ≠ done | Erreur |
| Affectation story/sprint | add_story_to_sprint | OK |
| Parité REST/MCP | Mêmes services, mêmes règles | OK |

---

## Points clés à mentionner pendant la démo

1. **Parité REST / MCP** : les tools MCP appellent les mêmes services que les routes REST — même validation, mêmes règles métier, mêmes erreurs.
2. **Descriptions optimisées LLM** : chaque tool a une description claire pour guider le LLM.
3. **Sécurité** : transport stdio (pas d'exposition réseau), même RBAC que REST.
4. **Architecture** : séparation API ↔ Services ↔ ORM ↔ DB (défense en profondeur).
