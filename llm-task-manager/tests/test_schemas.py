"""
Tests unitaires pour les schémas Pydantic (app/models/schemas.py).

Couvre :
- Validation des champs obligatoires
- Longueurs maximales
- Valeurs d'enum invalides
- Valeurs par défaut
- Construction depuis des objets ORM (from_attributes)
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.domain import (
    CommentTargetType,
    EpicStatus,
    SprintStatus,
    StoryPriority,
    StoryStatus,
)
from app.models.schemas import (
    CommentCreate,
    DocumentCreate,
    EpicCreate,
    EpicUpdate,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
    SprintCreate,
    StoryCreate,
    StoryOut,
    StoryUpdate,
)


# ---------------------------------------------------------------------------
# ProjectCreate
# ---------------------------------------------------------------------------


class TestProjectCreate:
    def test_valid_project(self):
        p = ProjectCreate(name="Mon projet", description="Desc")
        assert p.name == "Mon projet"
        assert p.description == "Desc"

    def test_name_required(self):
        with pytest.raises(ValidationError) as exc_info:
            ProjectCreate(description="oops")  # type: ignore[call-arg]
        assert "name" in str(exc_info.value)

    def test_name_max_length(self):
        with pytest.raises(ValidationError):
            ProjectCreate(name="x" * 256)

    def test_description_optional(self):
        p = ProjectCreate(name="Projet")
        assert p.description is None


# ---------------------------------------------------------------------------
# ProjectUpdate
# ---------------------------------------------------------------------------


class TestProjectUpdate:
    def test_partial_update_name_only(self):
        u = ProjectUpdate(name="Nouveau nom")
        assert u.name == "Nouveau nom"
        assert u.description is None

    def test_empty_update(self):
        u = ProjectUpdate()
        assert u.name is None
        assert u.description is None


# ---------------------------------------------------------------------------
# ProjectOut (from_attributes)
# ---------------------------------------------------------------------------


class TestProjectOut:
    def test_from_attributes(self):
        """Simule la sérialisation depuis un objet ORM."""
        now = datetime.utcnow()
        uid = uuid4()

        class FakeProject:
            id = uid
            name = "Proj"
            description = None
            created_at = now
            updated_at = now

        out = ProjectOut.model_validate(FakeProject())
        assert out.id == uid
        assert out.name == "Proj"


# ---------------------------------------------------------------------------
# EpicCreate / EpicUpdate
# ---------------------------------------------------------------------------


class TestEpicSchemas:
    def test_epic_create_with_defaults(self):
        e = EpicCreate(project_id=uuid4(), title="Epic 1")
        assert e.status == EpicStatus.BACKLOG

    def test_epic_create_title_required(self):
        with pytest.raises(ValidationError):
            EpicCreate(project_id=uuid4())  # type: ignore[call-arg]

    def test_epic_create_title_max_length(self):
        with pytest.raises(ValidationError):
            EpicCreate(project_id=uuid4(), title="e" * 256)

    def test_epic_update_partial(self):
        u = EpicUpdate(title="Nouveau titre")
        data = u.model_dump(exclude_unset=True)
        assert data == {"title": "Nouveau titre"}

    def test_epic_create_invalid_status(self):
        with pytest.raises(ValidationError):
            EpicCreate(project_id=uuid4(), title="Epic", status="inexistant")


# ---------------------------------------------------------------------------
# StoryCreate / StoryUpdate / StoryOut
# ---------------------------------------------------------------------------


class TestStorySchemas:
    def test_story_create_defaults(self):
        s = StoryCreate(project_id=uuid4(), title="Story 1")
        assert s.status == StoryStatus.BACKLOG
        assert s.priority == StoryPriority.MEDIUM
        assert s.story_points == 0
        assert s.assignee is None

    def test_story_create_title_required(self):
        with pytest.raises(ValidationError):
            StoryCreate(project_id=uuid4())  # type: ignore[call-arg]

    def test_story_create_title_max_length(self):
        with pytest.raises(ValidationError):
            StoryCreate(project_id=uuid4(), title="s" * 256)

    def test_story_create_invalid_status(self):
        with pytest.raises(ValidationError):
            StoryCreate(project_id=uuid4(), title="Story", status="invalid_status")

    def test_story_create_invalid_priority(self):
        with pytest.raises(ValidationError):
            StoryCreate(project_id=uuid4(), title="Story", priority="urgent")

    def test_story_update_partial(self):
        u = StoryUpdate(story_points=5)
        data = u.model_dump(exclude_unset=True)
        assert data == {"story_points": 5}

    def test_story_update_all_none(self):
        u = StoryUpdate()
        data = u.model_dump(exclude_unset=True)
        assert data == {}

    def test_story_out_from_attributes(self):
        now = datetime.utcnow()
        uid = uuid4()
        pid = uuid4()

        class FakeStory:
            id = uid
            project_id = pid
            epic_id = None
            title = "Story"
            status = StoryStatus.BACKLOG
            priority = StoryPriority.LOW
            story_points = 3
            assignee = "alice"
            created_at = now
            updated_at = now

        out = StoryOut.model_validate(FakeStory())
        assert out.id == uid
        assert out.story_points == 3
        assert out.assignee == "alice"


# ---------------------------------------------------------------------------
# SprintCreate
# ---------------------------------------------------------------------------


class TestSprintSchemas:
    def test_sprint_create_defaults(self):
        s = SprintCreate(project_id=uuid4(), name="Sprint 1")
        assert s.status == SprintStatus.PLANNED
        assert s.start_date is None
        assert s.end_date is None

    def test_sprint_create_name_required(self):
        with pytest.raises(ValidationError):
            SprintCreate(project_id=uuid4())  # type: ignore[call-arg]

    def test_sprint_create_invalid_status(self):
        with pytest.raises(ValidationError):
            SprintCreate(project_id=uuid4(), name="Sprint", status="running")


# ---------------------------------------------------------------------------
# CommentCreate
# ---------------------------------------------------------------------------


class TestCommentSchemas:
    def test_comment_create_valid(self):
        c = CommentCreate(
            project_id=uuid4(),
            target_type=CommentTargetType.STORY,
            target_id=uuid4(),
            content="Un commentaire",
        )
        assert c.content == "Un commentaire"

    def test_comment_content_required(self):
        with pytest.raises(ValidationError):
            CommentCreate(
                project_id=uuid4(),
                target_type=CommentTargetType.EPIC,
                target_id=uuid4(),
            )  # type: ignore[call-arg]

    def test_comment_content_max_length(self):
        with pytest.raises(ValidationError):
            CommentCreate(
                project_id=uuid4(),
                target_type=CommentTargetType.STORY,
                target_id=uuid4(),
                content="x" * 2001,
            )

    def test_comment_invalid_target_type(self):
        with pytest.raises(ValidationError):
            CommentCreate(
                project_id=uuid4(),
                target_type="task",  # type: ignore[arg-type]
                target_id=uuid4(),
                content="Test",
            )


# ---------------------------------------------------------------------------
# DocumentCreate
# ---------------------------------------------------------------------------


class TestDocumentSchemas:
    def test_document_create_valid(self):
        d = DocumentCreate(
            project_id=uuid4(),
            title="Doc",
            content="Contenu",
        )
        assert d.template_key is None

    def test_document_create_title_required(self):
        with pytest.raises(ValidationError):
            DocumentCreate(project_id=uuid4(), content="Contenu")  # type: ignore[call-arg]

    def test_document_create_title_max_length(self):
        with pytest.raises(ValidationError):
            DocumentCreate(project_id=uuid4(), title="d" * 256, content="ok")
