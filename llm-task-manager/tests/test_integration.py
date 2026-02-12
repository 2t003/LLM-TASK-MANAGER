"""
Tests d'intégration REST API.

Couvre :
- Scénario CRUD complet : Project → Epic → Story → Sprint → Comment → Document
- Scénarios d'erreur métier via l'API REST :
  - Transition de statut illégale (story)
  - Story points invalides
  - Clôture de sprint bloquée
  - Retrait d'une story non liée
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# CRUD complet : scénario nominal
# ---------------------------------------------------------------------------


class TestCRUDIntegration:
    """Scénario complet : création projet → epic → story → sprint → lien → workflow."""

    def test_full_crud_workflow(self, client: TestClient):
        # 1. Créer un projet
        resp = client.post("/v1/projects", json={"name": "IntegTest", "description": "Test project"})
        assert resp.status_code == 201
        project = resp.json()
        project_id = project["id"]
        assert project["name"] == "IntegTest"

        # 2. Lister les projets
        resp = client.get("/v1/projects")
        assert resp.status_code == 200
        projects = resp.json()
        assert any(p["id"] == project_id for p in projects)

        # 3. Créer un epic
        resp = client.post("/v1/epics", json={"project_id": project_id, "title": "Epic Integ"})
        assert resp.status_code == 201
        epic = resp.json()
        epic_id = epic["id"]
        assert epic["status"] == "backlog"

        # 4. Créer une story liée à l'epic
        resp = client.post("/v1/stories", json={
            "project_id": project_id,
            "epic_id": epic_id,
            "title": "Story Integ",
            "story_points": 5,
            "priority": "high",
        })
        assert resp.status_code == 201
        story = resp.json()
        story_id = story["id"]
        assert story["story_points"] == 5
        assert story["priority"] == "high"
        assert story["epic_id"] == epic_id

        # 5. Lire la story
        resp = client.get(f"/v1/stories/{story_id}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Story Integ"

        # 6. Créer un sprint
        resp = client.post("/v1/sprints", json={
            "project_id": project_id,
            "name": "Sprint Integ",
        })
        assert resp.status_code == 201
        sprint = resp.json()
        sprint_id = sprint["id"]
        assert sprint["status"] == "planned"

        # 7. Démarrer le sprint
        resp = client.post(f"/v1/sprints/{sprint_id}/start")
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

        # 8. Lier la story au sprint
        resp = client.post(f"/v1/sprints/{sprint_id}/stories/{story_id}")
        assert resp.status_code == 204

        # 9. Faire avancer la story : backlog → todo → in_progress → in_review → done
        for new_status in ["todo", "in_progress", "in_review", "done"]:
            resp = client.patch(f"/v1/stories/{story_id}", json={"status": new_status})
            assert resp.status_code == 200
            assert resp.json()["status"] == new_status

        # 10. Clôturer le sprint (toutes les stories sont done)
        resp = client.post(f"/v1/sprints/{sprint_id}/close")
        assert resp.status_code == 200
        assert resp.json()["status"] == "closed"

    def test_create_and_list_comments(self, client: TestClient):
        # Créer projet + story
        resp = client.post("/v1/projects", json={"name": "CommentProj"})
        project_id = resp.json()["id"]

        resp = client.post("/v1/stories", json={
            "project_id": project_id, "title": "Comment Story", "story_points": 1,
        })
        story_id = resp.json()["id"]

        # Créer un commentaire
        resp = client.post("/v1/comments", json={
            "project_id": project_id,
            "target_type": "story",
            "target_id": story_id,
            "content": "Commentaire de test",
        })
        assert resp.status_code == 201
        comment = resp.json()
        assert comment["content"] == "Commentaire de test"
        assert comment["target_type"] == "story"

        # Lister les commentaires
        resp = client.get("/v1/comments")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_create_and_list_documents(self, client: TestClient):
        resp = client.post("/v1/projects", json={"name": "DocProj"})
        project_id = resp.json()["id"]

        resp = client.post("/v1/documents", json={
            "project_id": project_id,
            "title": "Doc Test",
            "content": "Contenu du document",
        })
        assert resp.status_code == 201
        doc = resp.json()
        assert doc["title"] == "Doc Test"

        resp = client.get("/v1/documents")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


# ---------------------------------------------------------------------------
# Scénarios d'erreur métier
# ---------------------------------------------------------------------------


class TestErrorScenarios:
    def test_invalid_story_points(self, client: TestClient):
        """Story points hors Fibonacci → 400."""
        resp = client.post("/v1/projects", json={"name": "ErrProj"})
        project_id = resp.json()["id"]

        resp = client.post("/v1/stories", json={
            "project_id": project_id,
            "title": "Bad points",
            "story_points": 4,
        })
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "INVALID_STORY_POINTS"

    def test_illegal_status_transition(self, client: TestClient):
        """Transition backlog → in_progress (saut) → 409."""
        resp = client.post("/v1/projects", json={"name": "TransProj"})
        project_id = resp.json()["id"]

        resp = client.post("/v1/stories", json={
            "project_id": project_id,
            "title": "Trans story",
            "story_points": 2,
        })
        story_id = resp.json()["id"]

        resp = client.patch(f"/v1/stories/{story_id}", json={"status": "in_progress"})
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "INVALID_STATUS_TRANSITION"

    def test_cannot_leave_done(self, client: TestClient):
        """Story en done ne peut pas revenir en arrière → 409."""
        resp = client.post("/v1/projects", json={"name": "DoneProj"})
        project_id = resp.json()["id"]

        resp = client.post("/v1/stories", json={
            "project_id": project_id, "title": "Done story", "story_points": 1,
        })
        story_id = resp.json()["id"]

        # Amener à done
        for s in ["todo", "in_progress", "in_review", "done"]:
            resp = client.patch(f"/v1/stories/{story_id}", json={"status": s})
            assert resp.status_code == 200

        # Tenter de revenir
        resp = client.patch(f"/v1/stories/{story_id}", json={"status": "in_review"})
        assert resp.status_code == 409

    def test_close_sprint_blocked(self, client: TestClient):
        """Clôture de sprint avec stories non done → 409."""
        resp = client.post("/v1/projects", json={"name": "CloseProj"})
        project_id = resp.json()["id"]

        # Sprint
        resp = client.post("/v1/sprints", json={"project_id": project_id, "name": "SprintBlock"})
        sprint_id = resp.json()["id"]
        client.post(f"/v1/sprints/{sprint_id}/start")

        # Story en backlog
        resp = client.post("/v1/stories", json={
            "project_id": project_id, "title": "Blocante", "story_points": 2,
        })
        story_id = resp.json()["id"]

        # Lier au sprint
        client.post(f"/v1/sprints/{sprint_id}/stories/{story_id}")

        # Tenter la clôture
        resp = client.post(f"/v1/sprints/{sprint_id}/close")
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "SPRINT_CLOSE_BLOCKED"

    def test_remove_unlinked_story(self, client: TestClient):
        """Retirer une story non liée → 404."""
        resp = client.post("/v1/projects", json={"name": "RemoveProj"})
        project_id = resp.json()["id"]

        resp = client.post("/v1/sprints", json={"project_id": project_id, "name": "SprintR"})
        sprint_id = resp.json()["id"]

        resp = client.post("/v1/stories", json={
            "project_id": project_id, "title": "Unlinked", "story_points": 1,
        })
        story_id = resp.json()["id"]

        resp = client.delete(f"/v1/sprints/{sprint_id}/stories/{story_id}")
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "ACTIVE_LINK_NOT_FOUND"

    def test_get_nonexistent_story(self, client: TestClient):
        """GET d'une story inexistante → 404."""
        resp = client.get(f"/v1/stories/{uuid4()}")
        assert resp.status_code == 404

    def test_update_nonexistent_story(self, client: TestClient):
        """PATCH d'une story inexistante → 404."""
        resp = client.patch(f"/v1/stories/{uuid4()}", json={"title": "Nope"})
        assert resp.status_code == 404

    def test_pydantic_validation_422(self, client: TestClient):
        """Payload invalide (champ manquant) → 422."""
        resp = client.post("/v1/projects", json={})
        assert resp.status_code == 422

    def test_story_with_invalid_status_value(self, client: TestClient):
        """Status invalide dans le payload → 422."""
        resp = client.post("/v1/projects", json={"name": "ValProj"})
        project_id = resp.json()["id"]

        resp = client.post("/v1/stories", json={
            "project_id": project_id,
            "title": "Bad status",
            "status": "yolo",
            "story_points": 1,
        })
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Filtres et recherche
# ---------------------------------------------------------------------------


class TestFiltersAndSearch:
    def test_list_stories_by_status(self, client: TestClient):
        resp = client.post("/v1/projects", json={"name": "FilterProj"})
        project_id = resp.json()["id"]

        # Créer 2 stories
        client.post("/v1/stories", json={
            "project_id": project_id, "title": "S1", "story_points": 1,
        })
        resp2 = client.post("/v1/stories", json={
            "project_id": project_id, "title": "S2", "story_points": 2,
        })
        s2_id = resp2.json()["id"]

        # Avancer S2 à todo
        client.patch(f"/v1/stories/{s2_id}", json={"status": "todo"})

        # Filtrer par status=todo
        resp = client.get("/v1/stories", params={"status": "todo"})
        assert resp.status_code == 200
        stories = resp.json()
        assert all(s["status"] == "todo" for s in stories)
        assert any(s["id"] == s2_id for s in stories)

    def test_list_sprints_by_status(self, client: TestClient):
        resp = client.post("/v1/projects", json={"name": "SprintFilter"})
        project_id = resp.json()["id"]

        resp = client.post("/v1/sprints", json={"project_id": project_id, "name": "SP1"})
        sp1_id = resp.json()["id"]

        client.post("/v1/sprints", json={"project_id": project_id, "name": "SP2"})

        # Démarrer SP1
        client.post(f"/v1/sprints/{sp1_id}/start")

        resp = client.get("/v1/sprints", params={"status": "active"})
        assert resp.status_code == 200
        sprints = resp.json()
        assert all(s["status"] == "active" for s in sprints)
