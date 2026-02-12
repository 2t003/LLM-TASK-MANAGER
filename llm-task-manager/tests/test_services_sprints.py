"""
Tests unitaires pour le service sprints (app/services/sprints.py).

Couvre :
- Démarrage d'un sprint (planned → active)
- Clôture d'un sprint (bloquée si stories non done)
- Affectation story ↔ sprint (StorySprintHistory)
- Retrait de story du sprint
- Une story ne peut être active que dans un seul sprint
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlmodel import Session

from app.models.domain import (
    Project,
    Sprint,
    SprintStatus,
    Story,
    StorySprintHistory,
    StoryStatus,
)
from app.services.errors import DomainError
from app.services.sprints import (
    add_story_to_sprint,
    close_sprint,
    remove_story_from_sprint,
    start_sprint,
)


# ---------------------------------------------------------------------------
# start_sprint
# ---------------------------------------------------------------------------


class TestStartSprint:
    def test_start_sprint_ok(self, db: Session, sprint: Sprint):
        result = start_sprint(db, sprint.id)
        assert result.status == SprintStatus.ACTIVE

    def test_start_sprint_not_found(self, db: Session):
        with pytest.raises(DomainError) as exc_info:
            start_sprint(db, uuid4())
        assert exc_info.value.code == "SPRINT_NOT_FOUND"
        assert exc_info.value.http_status == 404


# ---------------------------------------------------------------------------
# close_sprint
# ---------------------------------------------------------------------------


class TestCloseSprint:
    def test_close_sprint_no_stories(self, db: Session, sprint: Sprint):
        """Un sprint sans stories peut être clôturé."""
        sprint.status = SprintStatus.ACTIVE
        db.add(sprint)
        db.commit()

        result = close_sprint(db, sprint.id)
        assert result.status == SprintStatus.CLOSED

    def test_close_sprint_all_done(self, db: Session, project: Project, sprint: Sprint):
        """Un sprint dont toutes les stories sont done peut être clôturé."""
        sprint.status = SprintStatus.ACTIVE
        db.add(sprint)
        db.commit()

        # Créer une story en done
        story = Story(
            project_id=project.id,
            title="Done story",
            status=StoryStatus.DONE,
            story_points=3,
        )
        db.add(story)
        db.commit()
        db.refresh(story)

        # Lier au sprint
        link = StorySprintHistory(
            story_id=story.id, sprint_id=sprint.id, is_active=True,
        )
        db.add(link)
        db.commit()

        result = close_sprint(db, sprint.id)
        assert result.status == SprintStatus.CLOSED

    def test_close_sprint_blocked_by_undone_story(
        self, db: Session, project: Project, sprint: Sprint,
    ):
        """Impossible de clôturer si une story n'est pas en done."""
        sprint.status = SprintStatus.ACTIVE
        db.add(sprint)
        db.commit()

        story = Story(
            project_id=project.id,
            title="WIP story",
            status=StoryStatus.IN_PROGRESS,
            story_points=2,
        )
        db.add(story)
        db.commit()
        db.refresh(story)

        link = StorySprintHistory(
            story_id=story.id, sprint_id=sprint.id, is_active=True,
        )
        db.add(link)
        db.commit()

        with pytest.raises(DomainError) as exc_info:
            close_sprint(db, sprint.id)
        assert exc_info.value.code == "SPRINT_CLOSE_BLOCKED"
        assert exc_info.value.http_status == 409

    def test_close_sprint_not_found(self, db: Session):
        with pytest.raises(DomainError) as exc_info:
            close_sprint(db, uuid4())
        assert exc_info.value.code == "SPRINT_NOT_FOUND"

    def test_close_sprint_mixed_stories(
        self, db: Session, project: Project, sprint: Sprint,
    ):
        """Mix done + non-done → bloqué."""
        sprint.status = SprintStatus.ACTIVE
        db.add(sprint)
        db.commit()

        done_story = Story(
            project_id=project.id, title="Done", status=StoryStatus.DONE, story_points=1,
        )
        wip_story = Story(
            project_id=project.id, title="WIP", status=StoryStatus.TODO, story_points=2,
        )
        db.add_all([done_story, wip_story])
        db.commit()
        db.refresh(done_story)
        db.refresh(wip_story)

        for s in [done_story, wip_story]:
            db.add(StorySprintHistory(story_id=s.id, sprint_id=sprint.id, is_active=True))
        db.commit()

        with pytest.raises(DomainError) as exc_info:
            close_sprint(db, sprint.id)
        assert exc_info.value.code == "SPRINT_CLOSE_BLOCKED"


# ---------------------------------------------------------------------------
# add_story_to_sprint
# ---------------------------------------------------------------------------


class TestAddStoryToSprint:
    def test_add_story_ok(self, db: Session, sprint: Sprint, story: Story):
        add_story_to_sprint(db, sprint.id, story.id)

        # Vérifier qu'un lien actif existe
        from sqlmodel import select

        link = db.exec(
            select(StorySprintHistory).where(
                StorySprintHistory.story_id == story.id,
                StorySprintHistory.sprint_id == sprint.id,
                StorySprintHistory.is_active.is_(True),
            )
        ).first()
        assert link is not None

    def test_add_story_deactivates_previous_link(
        self, db: Session, project: Project, story: Story,
    ):
        """
        Ajouter une story à un 2ème sprint désactive le lien précédent.
        (Une story ne peut être active que dans un seul sprint.)
        """
        sprint1 = Sprint(project_id=project.id, name="Sprint A", status=SprintStatus.ACTIVE)
        sprint2 = Sprint(project_id=project.id, name="Sprint B", status=SprintStatus.ACTIVE)
        db.add_all([sprint1, sprint2])
        db.commit()
        db.refresh(sprint1)
        db.refresh(sprint2)

        add_story_to_sprint(db, sprint1.id, story.id)
        add_story_to_sprint(db, sprint2.id, story.id)

        from sqlmodel import select

        # Sprint 1 → lien inactif
        old_link = db.exec(
            select(StorySprintHistory).where(
                StorySprintHistory.story_id == story.id,
                StorySprintHistory.sprint_id == sprint1.id,
            )
        ).first()
        assert old_link is not None
        assert old_link.is_active is False

        # Sprint 2 → lien actif
        new_link = db.exec(
            select(StorySprintHistory).where(
                StorySprintHistory.story_id == story.id,
                StorySprintHistory.sprint_id == sprint2.id,
                StorySprintHistory.is_active.is_(True),
            )
        ).first()
        assert new_link is not None

    def test_add_nonexistent_story(self, db: Session, sprint: Sprint):
        with pytest.raises(DomainError) as exc_info:
            add_story_to_sprint(db, sprint.id, uuid4())
        assert exc_info.value.code == "SPRINT_OR_STORY_NOT_FOUND"

    def test_add_to_nonexistent_sprint(self, db: Session, story: Story):
        with pytest.raises(DomainError) as exc_info:
            add_story_to_sprint(db, uuid4(), story.id)
        assert exc_info.value.code == "SPRINT_OR_STORY_NOT_FOUND"


# ---------------------------------------------------------------------------
# remove_story_from_sprint
# ---------------------------------------------------------------------------


class TestRemoveStoryFromSprint:
    def test_remove_story_ok(self, db: Session, sprint: Sprint, story: Story):
        add_story_to_sprint(db, sprint.id, story.id)
        remove_story_from_sprint(db, sprint.id, story.id)

        from sqlmodel import select

        link = db.exec(
            select(StorySprintHistory).where(
                StorySprintHistory.story_id == story.id,
                StorySprintHistory.sprint_id == sprint.id,
            )
        ).first()
        assert link is not None
        assert link.is_active is False

    def test_remove_no_active_link(self, db: Session, sprint: Sprint, story: Story):
        """Retirer une story non liée lève une erreur."""
        with pytest.raises(DomainError) as exc_info:
            remove_story_from_sprint(db, sprint.id, story.id)
        assert exc_info.value.code == "ACTIVE_LINK_NOT_FOUND"
