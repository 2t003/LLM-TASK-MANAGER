# LLM Task Manager — Plan Phase 2 (Implémentation & Déploiement)

Ce document sert de **guide de travail pour l’IA (Claude/Cursor)** afin d’implémenter et déployer le service conformément :

- au sujet du TP (`tp_final_evaluation.md`), **Phase 2 — Implémentation et déploiement** ;
- à l’architecture définie dans `ARCHITECTURE.md` (Business, Application, Data, Technology, Security).

Objectif final : **repo GitHub + service FastAPI déployé sur Cloud Run + serveur MCP fonctionnel**, avec un niveau **“Satisfaisant/Excellent”** dans chaque sous-partie du barème.

---

## 1. Contexte & contraintes globales

- **Produit** : LLM Task Manager (gestionnaire de tâches natif LLM, 6 entités : Projet, Epic, Story, Sprint, Commentaire, Document).
- **Points d’entrée** :
  - API **REST** `/v1/...`
  - **MCP tools** (serveur MCP Python `mcp`)
- **Infra cible** (cf. `ARCHITECTURE.md`) :
  - **Cloud Run** (FastAPI + MCP, monolithe modulaire)
  - **Cloud SQL PostgreSQL**
  - **Cloud Build** + **Artifact Registry**

### Stack imposée par le sujet

- Python ≥ 3.11
- Gestion dépendances : `uv`
- API : FastAPI
- Validation : Pydantic v2
- ORM : SQLAlchemy ou SQLModel (préféré dans `ARCHITECTURE.md`)
- DB : Cloud SQL PostgreSQL
- Déploiement : Cloud Run (`europe-west1`)
- Protocole LLM : SDK Python `mcp`

---

## 2. État de départ attendu

Le repo contient déjà :

- `ARCHITECTURE.md` complet (Business, Application, Data, Technology, Security) ;
- un squelette de projet Python :
  - `app/main.py` : app FastAPI avec `/health` et inclusion d’un router `/v1`;
  - `app/api/`, `app/models/`, `app/services/`, `app/db/`, `app/mcp/` : paquets vides documentés ;
  - `pyproject.toml` : dépendances de base (`fastapi`, `uvicorn`, `pydantic`, `sqlalchemy`, `sqlmodel`, `psycopg[binary]`, `mcp`) ;
  - `Dockerfile` : image Python 3.11 + Uvicorn servant `app.main:app`.

Si certains de ces éléments manquent, les **créer d’abord** avant de poursuivre les étapes ci-dessous.

---

## 3. Plan d’implémentation — API, MCP, Data, Tests (Phase 2.1)

Chaque étape ci-dessous doit viser au minimum le niveau **“Satisfaisant”** du barème, idéalement **“Excellent”**.

### Étape 1 — Modèle de données & ORM (SQLModel / SQLAlchemy)

**Objectif** : Implémenter le schéma SQL décrit dans `ARCHITECTURE.md` (mermaid ERD) dans `app/models/` via SQLModel (ou SQLAlchemy + ORM classique).

- Créer les modèles principaux :
  - `Project`, `Epic`, `Story`, `Sprint`, `Comment`, `Document`,
  - table de jonction `StorySprintHistory`,
  - `DocumentTemplate` pour les templates prédéfinis.
- Respecter les contraintes de `ARCHITECTURE.md` :
  - FKs, `UNIQUE` (nom projet, contraintes de mapping story/sprint),
  - `CHECK` (ex : `story_points IN (0,1,2,3,5,8,13)`),
  - colonnes `created_at` / `updated_at`.

**Critères de réussite (barème Data Architecture — “Satisfaisant/Excellent”)** :

- Modèles alignés sur l’ERD.
- Contraintes SQL explicites (FK, CHECK, UNIQUE).
- Champs et types cohérents avec les règles métier (statuts, priorités, etc.).

---

### Étape 2 — Couche DB & migrations

**Objectif** : Créer la couche d’accès BD dans `app/db/` et un système de migrations.

- Dans `app/db/` :
  - définir un `create_engine` SQLAlchemy/SQLModel,
  - intégrer une configuration de pool adaptée à Cloud Run (ex. `pool_size=5`, `max_overflow=5`),
  - exposer une dépendance FastAPI pour obtenir une session DB par requête.
- Configurer **Alembic** (ou équivalent) :
  - fichier `alembic.ini` + dossier `alembic/`,
  - script d’auto-génération des migrations basé sur les modèles,
  - commande simple type `alembic upgrade head`.

**Critères de réussite (barème Persistence Cloud SQL — “Excellent”)** :

- Schéma effectif en DB conforme à `ARCHITECTURE.md`.
- Migrations rejouables, proprement versionnées.

---

### Étape 3 — Modèles Pydantic & validation d’entrée

**Objectif** : Définir les schémas d’entrée/sortie dans `app/models/` pour chaque entité.

- Créer des modèles Pydantic v2 pour :
  - créations (`CreateProject`, `CreateStory`, etc.),
  - mises à jour (`UpdateEpic`, `UpdateStory`, etc.),
  - réponses (`ProjectOut`, `StoryOut`, etc.).
- Implémenter les validations métier de base côté schémas :
  - formats (UUID), longueurs max, enums pour `status`, `priority`, `story_points`.

**Critères de réussite (barème Qualité du code + Validation)** :

- Tous les endpoints REST utilisent des modèles Pydantic.
- Les erreurs de validation renvoient des `422` structurés.

---

### Étape 4 — API REST fonctionnelle pour les 6 entités

**Objectif** : Implémenter les endpoints `/v1/...` listés dans `ARCHITECTURE.md` dans `app/api/`.

- Créer des modules par ressource :
  - `app/api/projects.py`
  - `app/api/epics.py`
  - `app/api/stories.py`
  - `app/api/sprints.py`
  - `app/api/comments.py`
  - `app/api/documents.py`
- Pour chaque ressource, implémenter les routes REST décrites dans `ARCHITECTURE.md` :
  - CRUD + recherche + filtrage (status, priority, assignee, sprint_id…),
  - respect des codes HTTP (201, 200, 400, 404, 409, etc.).
- Brancher les routes sur la couche service (voir Étape 5).

**Critères de réussite (barème API REST — “Excellent”)** :

- CRUD complet sur les 6 entités.
- Filtrage et recherche opérationnels.
- Workflow de statuts respecté (voir Étape 5).

---

### Étape 5 — Logique métier & règles de domaine (Service Layer)

**Objectif** : Implémenter les règles métier critiques décrites dans `ARCHITECTURE.md` dans `app/services/`.

- Créer des services dédiés :
  - `ProjectService`, `EpicService`, `StoryService`, `SprintService`, `CommentService`, `DocumentService`.
- Implémenter au moins les règles suivantes :
  - Story points dans la suite de Fibonacci (0,1,2,3,5,8,13).
  - Workflow strict des statuts (`backlog → todo → in_progress → in_review → done`) sans saut ni retour depuis `done`.
  - Clôture de sprint possible **uniquement** si toutes les stories sont `done`.
  - Une story ne peut appartenir qu’à un **seul sprint actif** (gestion via `StorySprintHistory`).
  - Validation humaine obligatoire pour les actions structurantes (drapeau “pending confirmation” ou endpoint de confirmation explicite).

**Critères de réussite (barème Application Architecture + Implémentation)** :

- Règles métier centralisées dans la couche services.
- Violations renvoyant les bons codes (`400` ou `409`) avec messages explicites.

---

### Étape 6 — Serveur MCP & parité avec l’API REST

**Objectif** : Implémenter un serveur MCP dans `app/mcp/` exposant des tools parallèles aux endpoints REST.

- Utiliser le SDK Python `mcp` (`pip install mcp`).
- Créer des tools pour chaque entité (cf. `ARCHITECTURE.md`) :
  - `create_project`, `list_projects`, etc.
  - `create_epic`, `get_epic`, `update_epic`, `search_epics`, etc.
  - idem pour `Story`, `Sprint`, `Comment`, `Document`.
- Chaque tool :
  - possède une description claire pour un LLM,
  - utilise les mêmes modèles et services que l’API REST,
  - retourne des objets JSON structurés,
  - gère les erreurs métier de façon explicite (messages utiles au LLM).

**Critères de réussite (barème Serveur MCP — “Excellent”)** :

- Parité fonctionnelle REST / MCP.
- Descriptions optimisées pour la compréhension par un LLM.

---

### Étape 7 — Tests unitaires & d’intégration

**Objectif** : Couvrir la logique métier et les principaux flux REST par des tests dans `tests/`.

- Tests unitaires (Pytest) pour :
  - les modèles Pydantic (validation, erreurs attendues),
  - la couche services (règles métier clés, transitions statut, sprint close, story/sprint actif).
- Au moins un test d’intégration :
  - scénarios CRUD complet sur une ressource (ex. Project + Epic + Story),
  - scénarios d’erreur (transition illégale, story dans deux sprints actifs, etc.).

**Critères de réussite (barème Tests — “Excellent”)** :

- Tests couvrant cas nominaux et cas d’erreur.
- Tests d’intégration utilisant une DB de test (SQLite ou Postgres éphémère).

---

## 4. Plan de déploiement — Docker, Cloud Build, Cloud Run (Phase 2.2)

### Étape 8 — Vérification Docker & exécution locale

**Objectif** : S’assurer que le `Dockerfile` permet de lancer correctement l’API.

- Construire l’image localement :

```bash
docker build -t llm-task-manager:local .
```

- Lancer un container :

```bash
docker run -p 8080:8080 llm-task-manager:local
```

- Vérifier :
  - `GET http://localhost:8080/health` → `{"status": "ok"}`
  - `GET http://localhost:8080/docs` → Swagger OK.

---

### Étape 9 — Configuration Cloud Build (`cloudbuild.yaml`)

**Objectif** : Créer un pipeline CI/CD conforme à `ARCHITECTURE.md` et au barème Technology Architecture.

- À la racine du repo, créer `cloudbuild.yaml` avec les étapes :
  1. Checkout du code.
  2. Installation des dépendances (via `uv sync` ou `pip install -e .` selon choix).
  3. Lancement des tests (`pytest`).
  4. Build de l’image Docker et push vers Artifact Registry.
  5. Lancement des migrations DB (`alembic upgrade head`).
  6. Déploiement sur Cloud Run (`gcloud run deploy ...`).
  7. Vérification post-deploy (`curl https://.../health`).

**Critères de réussite (barème Technology Architecture + Bonus Pipeline)** :

- Pipeline qui tourne de bout en bout sur push/merge vers `main`.
- Échec du pipeline si tests cassés ou `/health` KO.

---

### Étape 10 — Déploiement Cloud Run

**Objectif** : Avoir un service FastAPI accessible publiquement (ou au moins pour la démo) en `europe-west1` avec `/health` OK.

- Paramètres typiques (alignés sur `ARCHITECTURE.md`) :
  - `min-instances: 0` (ou `1` pour limiter les cold starts),
  - `max-instances: 5`,
  - `concurrency: 20`,
  - `cpu: 1`, `memory: 512Mi`.
- Connecter Cloud Run à Cloud SQL (instance + connecteur).
- Injecter les variables d’environnement (ou accès Secret Manager) :
  - `DB_USER`, `DB_NAME`, `INSTANCE_CONNECTION_NAME`, `API_KEY`, etc.

**Critères de réussite (barème Cloud Run opérationnel — 2 pts)** :

- URL publique renvoyant `200` sur `/health`.
- Service déployé en `europe-west1`.

---

### Étape 11 — Préparation de la démo REST + MCP

**Objectif** : Faciliter la démo de 20 min demandée dans le sujet (REST + MCP).

- Préparer un **script de démo** :
  - création d’un projet, d’un epic, de stories, d’un sprint ;
  - démonstration des règles métier (transition interdite, sprint close bloqué, etc.) ;
  - utilisation de quelques templates de documents.
- Préparer une démo MCP :
  - config du serveur MCP dans Cursor/Claude,
  - appels `create_story`, `search_stories`, `start_sprint`, etc.

**Critères de réussite (barème Démonstration live — “Excellent”)** :

- Démo fluide et maîtrisée sur les deux canaux (REST + MCP).
- Capacité à expliquer les choix d’architecture et de sécurité pendant les questions.

---

## 5. Règles d’or pour toute contribution de l’IA

1. **Toujours respecter `ARCHITECTURE.md`** comme source de vérité :
   - Si le code diverge, adapter le code ou proposer une mise à jour documentée d’`ARCHITECTURE.md`.
2. **Ne jamais coder “hors scope”** :
   - pas de frontend, pas de notifications, pas de multi-tenant complexe.
3. **Préférer la séparation des responsabilités** :
   - API (FastAPI) ↔ Services ↔ Repositories/ORM ↔ DB.
4. **Sécurité par défaut** :
   - API key REST, RBAC, validation Pydantic, ORM paramétré (anti-SQLi).
5. **Tests avant déploiement** :
   - Toute nouvelle règle métier doit avoir au moins 1–2 tests associés.

Ce plan doit être suivi étape par étape par l’IA pour amener le projet depuis le squelette actuel jusqu’à un **service déployé, testable et démontrable** répondant aux exigences de la Phase 2 du TP. 

