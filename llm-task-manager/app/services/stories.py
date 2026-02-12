"""
Services métier pour les stories.

Règles implémentées ici :
- Story points limités à la suite de Fibonacci (0,1,2,3,5,8,13)
- Workflow strict des statuts :
  backlog -> todo -> in_progress -> in_review -> done
- Impossible de quitter l'état `done`
"""

from collections.abc import Mapping
from typing import Final
from uuid import UUID

from sqlmodel import Session

from app.models import Story
from app.models.domain import StoryStatus
from app.models.schemas import StoryCreate, StoryUpdate
from app.services.errors import DomainError


FIBONACCI_STORY_POINTS: Final[set[int]] = {0, 1, 2, 3, 5, 8, 13}

ALLOWED_TRANSITIONS: Final[Mapping[StoryStatus, set[StoryStatus]]] = {
    StoryStatus.BACKLOG: {StoryStatus.TODO},
    StoryStatus.TODO: {StoryStatus.IN_PROGRESS},
    StoryStatus.IN_PROGRESS: {StoryStatus.IN_REVIEW},
    StoryStatus.IN_REVIEW: {StoryStatus.DONE},
    StoryStatus.DONE: set(),
}


def _validate_story_points(points: int) -> None:
    if points not in FIBONACCI_STORY_POINTS:
        raise DomainError(
            code="INVALID_STORY_POINTS",
            message=f"story_points must be in {sorted(FIBONACCI_STORY_POINTS)}.",
            http_status=400,
        )


def _validate_status_transition(old: StoryStatus, new: StoryStatus) -> None:
    if old == new:
        return

    if old == StoryStatus.DONE and new != StoryStatus.DONE:
        raise DomainError(
            code="INVALID_STATUS_TRANSITION",
            message="Cannot transition from 'done' to another status.",
            http_status=409,
        )

    allowed = ALLOWED_TRANSITIONS.get(old, set())
    if new not in allowed:
        raise DomainError(
            code="INVALID_STATUS_TRANSITION",
            message=f"Invalid transition from '{old}' to '{new}'. Must follow the strict workflow.",
            http_status=409,
        )


def create_story(db: Session, payload: StoryCreate) -> Story:
    """Crée une story en appliquant les règles métier (points, statut)."""
    _validate_story_points(payload.story_points)

    story = Story(
        project_id=payload.project_id,
        epic_id=payload.epic_id,
        title=payload.title,
        status=payload.status,
        priority=payload.priority,
        story_points=payload.story_points,
        assignee=payload.assignee,
    )
    db.add(story)
    db.commit()
    db.refresh(story)
    return story


def update_story(db: Session, story_id: UUID, payload: StoryUpdate) -> Story:
    """Met à jour une story en validant transitions de statut et points."""
    story = db.get(Story, story_id)
    if not story:
        raise DomainError(
            code="STORY_NOT_FOUND",
            message="Story not found.",
            http_status=404,
        )

    data = payload.model_dump(exclude_unset=True)

    if "story_points" in data:
        _validate_story_points(data["story_points"])

    if "status" in data:
        _validate_status_transition(story.status, data["status"])

    for field, value in data.items():
        setattr(story, field, value)

    db.add(story)
    db.commit()
    db.refresh(story)
    return story


__all__ = ["create_story", "update_story"]

