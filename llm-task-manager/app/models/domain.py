"""
Modèles de domaine et schémas ORM (SQLModel) pour le LLM Task Manager.

Ces modèles implémentent le schéma décrit dans `ARCHITECTURE.md`
et servent de base à la couche de persistence (PostgreSQL / Cloud SQL).
"""

from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Column, Enum as SAEnum, SmallInteger
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    pass  # forward references résolues via les chaînes dans Relationship


# ---------------------------------------------------------------------------
# Enums métier (status, priorité, etc.)
# ---------------------------------------------------------------------------


class EpicStatus(str, Enum):
    BACKLOG = "backlog"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"


class StoryStatus(str, Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"


class StoryPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SprintStatus(str, Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    CLOSED = "closed"


class CommentTargetType(str, Enum):
    EPIC = "epic"
    STORY = "story"


# ---------------------------------------------------------------------------
# Modèles principaux
# ---------------------------------------------------------------------------


class Project(SQLModel, table=True):
    """Projet : conteneur principal des epics, stories, sprints, commentaires, documents."""

    __tablename__ = "projects"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    name: str = Field(index=True, max_length=255)
    description: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    epics: List["Epic"] = Relationship(back_populates="project")
    stories: List["Story"] = Relationship(back_populates="project")
    sprints: List["Sprint"] = Relationship(back_populates="project")
    comments: List["Comment"] = Relationship(back_populates="project")
    documents: List["Document"] = Relationship(back_populates="project")


class Epic(SQLModel, table=True):
    """Epic : regroupe un ensemble de stories liées à une initiative produit."""

    __tablename__ = "epics"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    project_id: UUID = Field(foreign_key="projects.id", index=True)
    title: str = Field(max_length=255)
    status: EpicStatus = Field(
        default=EpicStatus.BACKLOG,
        sa_column=Column(SAEnum(EpicStatus, name="epic_status")),
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    project: Project = Relationship(back_populates="epics")
    stories: List["Story"] = Relationship(back_populates="epic")


class Story(SQLModel, table=True):
    """Story : unité de travail estimée en story points."""

    __tablename__ = "stories"
    __table_args__ = (
        CheckConstraint(
            "story_points IN (0, 1, 2, 3, 5, 8, 13)",
            name="story_points_fibonacci_check",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    project_id: UUID = Field(foreign_key="projects.id", index=True)
    epic_id: Optional[UUID] = Field(default=None, foreign_key="epics.id", index=True)

    title: str = Field(max_length=255)

    status: StoryStatus = Field(
        default=StoryStatus.BACKLOG,
        sa_column=Column(SAEnum(StoryStatus, name="story_status")),
    )
    priority: StoryPriority = Field(
        default=StoryPriority.MEDIUM,
        sa_column=Column(SAEnum(StoryPriority, name="story_priority")),
    )

    story_points: int = Field(
        default=0,
        sa_column=Column(SmallInteger, nullable=False),
    )

    assignee: Optional[str] = Field(default=None, max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    project: Project = Relationship(back_populates="stories")
    epic: Optional[Epic] = Relationship(back_populates="stories")

    sprint_history: List["StorySprintHistory"] = Relationship(
        back_populates="story",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class Sprint(SQLModel, table=True):
    """Sprint : période de travail regroupant un ensemble de stories."""

    __tablename__ = "sprints"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    project_id: UUID = Field(foreign_key="projects.id", index=True)

    name: str = Field(max_length=255)
    status: SprintStatus = Field(
        default=SprintStatus.PLANNED,
        sa_column=Column(SAEnum(SprintStatus, name="sprint_status")),
    )

    start_date: Optional[date] = Field(default=None)
    end_date: Optional[date] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    project: Project = Relationship(back_populates="sprints")
    story_history: List["StorySprintHistory"] = Relationship(
        back_populates="sprint",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class StorySprintHistory(SQLModel, table=True):
    """
    Historique many-to-many entre Story et Sprint.

    Une story peut passer dans plusieurs sprints successifs,
    mais ne peut être active que dans un seul sprint à la fois.
    """

    __tablename__ = "story_sprint_history"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    story_id: UUID = Field(foreign_key="stories.id", index=True)
    sprint_id: UUID = Field(foreign_key="sprints.id", index=True)

    is_active: bool = Field(default=True, index=True)
    added_at: datetime = Field(default_factory=datetime.utcnow)
    removed_at: Optional[datetime] = Field(default=None)

    story: Story = Relationship(back_populates="sprint_history")
    sprint: Sprint = Relationship(back_populates="story_history")


class Comment(SQLModel, table=True):
    """Commentaire sur un epic ou une story."""

    __tablename__ = "comments"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    project_id: UUID = Field(foreign_key="projects.id", index=True)

    target_type: CommentTargetType = Field(
        sa_column=Column(SAEnum(CommentTargetType, name="comment_target_type")),
    )
    target_id: UUID = Field(index=True)

    content: str = Field(max_length=2000)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    project: Project = Relationship(back_populates="comments")


class DocumentTemplate(SQLModel, table=True):
    """Template de document prédéfini (Problem Statement, Product Vision, etc.)."""

    __tablename__ = "document_templates"

    key: str = Field(primary_key=True, max_length=100)
    name: str = Field(max_length=255)
    content: str
    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    documents: List["Document"] = Relationship(back_populates="template")


class Document(SQLModel, table=True):
    """Document rattaché à un projet, optionnellement basé sur un template."""

    __tablename__ = "documents"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    project_id: UUID = Field(foreign_key="projects.id", index=True)

    title: str = Field(max_length=255)
    content: str

    template_key: Optional[str] = Field(
        default=None,
        foreign_key="document_templates.key",
        index=True,
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    project: Project = Relationship(back_populates="documents")
    template: Optional[DocumentTemplate] = Relationship(back_populates="documents")


__all__ = [
    "Project",
    "Epic",
    "Story",
    "Sprint",
    "StorySprintHistory",
    "Comment",
    "DocumentTemplate",
    "Document",
    "EpicStatus",
    "StoryStatus",
    "StoryPriority",
    "SprintStatus",
    "CommentTargetType",
]

