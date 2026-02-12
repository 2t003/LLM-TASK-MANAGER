"""
Tests unitaires pour le service stories (app/services/stories.py).

Couvre :
- Validation des story points (suite de Fibonacci)
- Workflow strict des statuts (backlog → todo → in_progress → in_review → done)
- Impossibilité de quitter l'état done
- Création et mise à jour de stories
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlmodel import Session

from app.models.domain import Project, Story, StoryPriority, StoryStatus
from app.models.schemas import StoryCreate, StoryUpdate
from app.services.errors import DomainError
from app.services.stories import (
    ALLOWED_TRANSITIONS,
    FIBONACCI_STORY_POINTS,
    _validate_status_transition,
    _validate_story_points,
    create_story,
    update_story,
)


# ---------------------------------------------------------------------------
# _validate_story_points
# ---------------------------------------------------------------------------


class TestValidateStoryPoints:
    @pytest.mark.parametrize("points", sorted(FIBONACCI_STORY_POINTS))
    def test_valid_fibonacci_values(self, points: int):
        """Les valeurs 0,1,2,3,5,8,13 sont acceptées."""
        _validate_story_points(points)  # Ne doit pas lever d'exception

    @pytest.mark.parametrize("points", [4, 6, 7, 9, 10, 11, 12, 14, -1, 100])
    def test_invalid_story_points(self, points: int):
        with pytest.raises(DomainError) as exc_info:
            _validate_story_points(points)
        assert exc_info.value.code == "INVALID_STORY_POINTS"
        assert exc_info.value.http_status == 400


# ---------------------------------------------------------------------------
# _validate_status_transition
# ---------------------------------------------------------------------------


class TestValidateStatusTransition:
    def test_same_status_is_noop(self):
        """Passer du même statut au même statut ne lève pas d'erreur."""
        for status in StoryStatus:
            _validate_status_transition(status, status)

    def test_valid_transitions(self):
        """Chaque transition autorisée doit passer sans erreur."""
        valid_path = [
            (StoryStatus.BACKLOG, StoryStatus.TODO),
            (StoryStatus.TODO, StoryStatus.IN_PROGRESS),
            (StoryStatus.IN_PROGRESS, StoryStatus.IN_REVIEW),
            (StoryStatus.IN_REVIEW, StoryStatus.DONE),
        ]
        for old, new in valid_path:
            _validate_status_transition(old, new)

    def test_cannot_leave_done(self):
        """Impossible de quitter l'état done."""
        for target in [StoryStatus.BACKLOG, StoryStatus.TODO, StoryStatus.IN_PROGRESS, StoryStatus.IN_REVIEW]:
            with pytest.raises(DomainError) as exc_info:
                _validate_status_transition(StoryStatus.DONE, target)
            assert exc_info.value.code == "INVALID_STATUS_TRANSITION"
            assert exc_info.value.http_status == 409

    def test_skip_status_forward(self):
        """Sauter un statut (backlog → in_progress) est interdit."""
        with pytest.raises(DomainError) as exc_info:
            _validate_status_transition(StoryStatus.BACKLOG, StoryStatus.IN_PROGRESS)
        assert exc_info.value.code == "INVALID_STATUS_TRANSITION"

    def test_backward_transition(self):
        """Revenir en arrière (in_progress → todo) est interdit."""
        with pytest.raises(DomainError) as exc_info:
            _validate_status_transition(StoryStatus.IN_PROGRESS, StoryStatus.TODO)
        assert exc_info.value.code == "INVALID_STATUS_TRANSITION"

    def test_backlog_to_done_directly(self):
        """Sauter directement de backlog à done est interdit."""
        with pytest.raises(DomainError):
            _validate_status_transition(StoryStatus.BACKLOG, StoryStatus.DONE)


# ---------------------------------------------------------------------------
# create_story
# ---------------------------------------------------------------------------


class TestCreateStory:
    def test_create_story_valid(self, db: Session, project: Project):
        payload = StoryCreate(
            project_id=project.id,
            title="Nouvelle story",
            story_points=5,
        )
        story = create_story(db, payload)
        assert story.id is not None
        assert story.title == "Nouvelle story"
        assert story.story_points == 5
        assert story.status == StoryStatus.BACKLOG

    def test_create_story_invalid_points(self, db: Session, project: Project):
        payload = StoryCreate(
            project_id=project.id,
            title="Bad points",
            story_points=4,
        )
        with pytest.raises(DomainError) as exc_info:
            create_story(db, payload)
        assert exc_info.value.code == "INVALID_STORY_POINTS"

    def test_create_story_with_all_fields(self, db: Session, project: Project, epic):
        payload = StoryCreate(
            project_id=project.id,
            epic_id=epic.id,
            title="Full story",
            status=StoryStatus.BACKLOG,
            priority=StoryPriority.HIGH,
            story_points=8,
            assignee="bob",
        )
        story = create_story(db, payload)
        assert story.epic_id == epic.id
        assert story.priority == StoryPriority.HIGH
        assert story.assignee == "bob"


# ---------------------------------------------------------------------------
# update_story
# ---------------------------------------------------------------------------


class TestUpdateStory:
    def test_update_title(self, db: Session, story: Story):
        payload = StoryUpdate(title="Titre modifié")
        updated = update_story(db, story.id, payload)
        assert updated.title == "Titre modifié"

    def test_update_valid_transition(self, db: Session, story: Story):
        """backlog → todo est autorisé."""
        payload = StoryUpdate(status=StoryStatus.TODO)
        updated = update_story(db, story.id, payload)
        assert updated.status == StoryStatus.TODO

    def test_update_invalid_transition(self, db: Session, story: Story):
        """backlog → in_progress est interdit (saut)."""
        payload = StoryUpdate(status=StoryStatus.IN_PROGRESS)
        with pytest.raises(DomainError) as exc_info:
            update_story(db, story.id, payload)
        assert exc_info.value.code == "INVALID_STATUS_TRANSITION"

    def test_update_story_points_valid(self, db: Session, story: Story):
        payload = StoryUpdate(story_points=13)
        updated = update_story(db, story.id, payload)
        assert updated.story_points == 13

    def test_update_story_points_invalid(self, db: Session, story: Story):
        payload = StoryUpdate(story_points=7)
        with pytest.raises(DomainError) as exc_info:
            update_story(db, story.id, payload)
        assert exc_info.value.code == "INVALID_STORY_POINTS"

    def test_update_nonexistent_story(self, db: Session):
        payload = StoryUpdate(title="Nope")
        with pytest.raises(DomainError) as exc_info:
            update_story(db, uuid4(), payload)
        assert exc_info.value.code == "STORY_NOT_FOUND"
        assert exc_info.value.http_status == 404

    def test_full_workflow(self, db: Session, story: Story):
        """Parcours complet : backlog → todo → in_progress → in_review → done."""
        statuses = [
            StoryStatus.TODO,
            StoryStatus.IN_PROGRESS,
            StoryStatus.IN_REVIEW,
            StoryStatus.DONE,
        ]
        for s in statuses:
            story = update_story(db, story.id, StoryUpdate(status=s))
        assert story.status == StoryStatus.DONE

    def test_cannot_leave_done_via_update(self, db: Session, story: Story):
        """Une fois en done, impossible de revenir en arrière."""
        # Amener à done
        for s in [StoryStatus.TODO, StoryStatus.IN_PROGRESS, StoryStatus.IN_REVIEW, StoryStatus.DONE]:
            story = update_story(db, story.id, StoryUpdate(status=s))

        with pytest.raises(DomainError) as exc_info:
            update_story(db, story.id, StoryUpdate(status=StoryStatus.IN_REVIEW))
        assert exc_info.value.code == "INVALID_STATUS_TRANSITION"
