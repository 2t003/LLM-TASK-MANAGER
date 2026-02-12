"""
Services métier pour les sprints.

Règles implémentées ici :
- Clôture de sprint uniquement si toutes les stories actives sont `done`
- Gestion de l'affectation story/sprint via StorySprintHistory
"""

from typing import Iterable
from uuid import UUID

from sqlmodel import Session, select

from app.models import Sprint, Story, StorySprintHistory
from app.models.domain import SprintStatus, StoryStatus
from app.services.errors import DomainError


def start_sprint(db: Session, sprint_id: UUID) -> Sprint:
    sprint = db.get(Sprint, sprint_id)
    if not sprint:
        raise DomainError(
            code="SPRINT_NOT_FOUND",
            message="Sprint not found.",
            http_status=404,
        )

    sprint.status = SprintStatus.ACTIVE
    db.add(sprint)
    db.commit()
    db.refresh(sprint)
    return sprint


def close_sprint(db: Session, sprint_id: UUID) -> Sprint:
    """Clôture un sprint si toutes les stories associées sont `done`."""
    sprint = db.get(Sprint, sprint_id)
    if not sprint:
        raise DomainError(
            code="SPRINT_NOT_FOUND",
            message="Sprint not found.",
            http_status=404,
        )

    # Récupérer toutes les stories actives dans ce sprint
    active_links: Iterable[StorySprintHistory] = db.exec(
        select(StorySprintHistory).where(
            StorySprintHistory.sprint_id == sprint_id,
            StorySprintHistory.is_active.is_(True),
        )
    ).all()

    story_ids = [link.story_id for link in active_links]
    if story_ids:
        stories: Iterable[Story] = db.exec(
            select(Story).where(Story.id.in_(story_ids))
        ).all()
        not_done = [s for s in stories if s.status != StoryStatus.DONE]
        if not_done:
            raise DomainError(
                code="SPRINT_CLOSE_BLOCKED",
                message="Cannot close sprint: some stories are not in 'done' status.",
                http_status=409,
            )

    sprint.status = SprintStatus.CLOSED
    db.add(sprint)
    db.commit()
    db.refresh(sprint)
    return sprint


def add_story_to_sprint(db: Session, sprint_id: UUID, story_id: UUID) -> None:
    sprint = db.get(Sprint, sprint_id)
    story = db.get(Story, story_id)
    if not sprint or not story:
        raise DomainError(
            code="SPRINT_OR_STORY_NOT_FOUND",
            message="Sprint or story not found.",
            http_status=404,
        )

    # Désactiver les éventuelles entrées actives existantes pour cette story
    active_entries = db.exec(
        select(StorySprintHistory).where(
            StorySprintHistory.story_id == story_id,
            StorySprintHistory.is_active.is_(True),
        )
    ).all()
    for entry in active_entries:
        entry.is_active = False
        db.add(entry)

    link = StorySprintHistory(story_id=story_id, sprint_id=sprint_id, is_active=True)
    db.add(link)
    db.commit()


def remove_story_from_sprint(db: Session, sprint_id: UUID, story_id: UUID) -> None:
    link = db.exec(
        select(StorySprintHistory).where(
            StorySprintHistory.story_id == story_id,
            StorySprintHistory.sprint_id == sprint_id,
            StorySprintHistory.is_active.is_(True),
        )
    ).first()

    if not link:
        raise DomainError(
            code="ACTIVE_LINK_NOT_FOUND",
            message="Active story/sprint link not found.",
            http_status=404,
        )

    link.is_active = False
    db.add(link)
    db.commit()


__all__ = ["start_sprint", "close_sprint", "add_story_to_sprint", "remove_story_from_sprint"]

