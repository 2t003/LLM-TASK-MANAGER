"""
Schémas Pydantic (v2) pour les entrées/sorties de l'API REST et des tools MCP.

Ils sont séparés des modèles ORM (`domain.py`) afin de :
- contrôler finement la validation et les payloads exposés
- éviter de divulguer des champs internes (ex: timestamps, IDs) lorsque ce n'est pas souhaité
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.domain import (
    CommentTargetType,
    EpicStatus,
    SprintStatus,
    StoryPriority,
    StoryStatus,
)


# ---------------------------------------------------------------------------
# Base models
# ---------------------------------------------------------------------------


class ORMBaseModel(BaseModel):
    """Base pour les modèles de sortie construits à partir d'objets ORM."""

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------


class ProjectBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    """Payload pour la création de projet."""


class ProjectUpdate(BaseModel):
    """Payload pour la mise à jour partielle de projet."""

    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None


class ProjectOut(ORMBaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Epic
# ---------------------------------------------------------------------------


class EpicBase(BaseModel):
    title: str = Field(..., max_length=255)
    status: EpicStatus = Field(default=EpicStatus.BACKLOG)


class EpicCreate(EpicBase):
    project_id: UUID


class EpicUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    status: Optional[EpicStatus] = None


class EpicOut(ORMBaseModel):
    id: UUID
    project_id: UUID
    title: str
    status: EpicStatus
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Story
# ---------------------------------------------------------------------------


class StoryBase(BaseModel):
    title: str = Field(..., max_length=255)
    status: StoryStatus = Field(default=StoryStatus.BACKLOG)
    priority: StoryPriority = Field(default=StoryPriority.MEDIUM)
    story_points: int = Field(
        default=0,
        description="Story points dans la suite de Fibonacci : 0,1,2,3,5,8,13.",
    )
    assignee: Optional[str] = Field(default=None, max_length=255)


class StoryCreate(StoryBase):
    project_id: UUID
    epic_id: Optional[UUID] = None


class StoryUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    status: Optional[StoryStatus] = None
    priority: Optional[StoryPriority] = None
    story_points: Optional[int] = None
    assignee: Optional[str] = Field(default=None, max_length=255)
    epic_id: Optional[UUID] = None


class StoryOut(ORMBaseModel):
    id: UUID
    project_id: UUID
    epic_id: Optional[UUID]
    title: str
    status: StoryStatus
    priority: StoryPriority
    story_points: int
    assignee: Optional[str]
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Sprint
# ---------------------------------------------------------------------------


class SprintBase(BaseModel):
    name: str = Field(..., max_length=255)
    status: SprintStatus = Field(default=SprintStatus.PLANNED)
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class SprintCreate(SprintBase):
    project_id: UUID


class SprintUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    status: Optional[SprintStatus] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class SprintOut(ORMBaseModel):
    id: UUID
    project_id: UUID
    name: str
    status: SprintStatus
    start_date: Optional[date]
    end_date: Optional[date]
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Comment
# ---------------------------------------------------------------------------


class CommentCreate(BaseModel):
    project_id: UUID
    target_type: CommentTargetType
    target_id: UUID
    content: str = Field(..., max_length=2000)


class CommentOut(ORMBaseModel):
    id: UUID
    project_id: UUID
    target_type: CommentTargetType
    target_id: UUID
    content: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Document & templates
# ---------------------------------------------------------------------------


class DocumentTemplateOut(ORMBaseModel):
    key: str
    name: str
    content: str
    version: int
    created_at: datetime


class DocumentBase(BaseModel):
    title: str = Field(..., max_length=255)
    content: str
    template_key: Optional[str] = Field(
        default=None, description="Clé du template utilisé, si applicable."
    )


class DocumentCreate(DocumentBase):
    project_id: UUID


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    content: Optional[str] = None
    template_key: Optional[str] = None


class DocumentOut(ORMBaseModel):
    id: UUID
    project_id: UUID
    title: str
    content: str
    template_key: Optional[str]
    created_at: datetime
    updated_at: datetime


__all__ = [
    # Projects
    "ProjectBase",
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectOut",
    # Epics
    "EpicBase",
    "EpicCreate",
    "EpicUpdate",
    "EpicOut",
    # Stories
    "StoryBase",
    "StoryCreate",
    "StoryUpdate",
    "StoryOut",
    # Sprints
    "SprintBase",
    "SprintCreate",
    "SprintUpdate",
    "SprintOut",
    # Comments
    "CommentCreate",
    "CommentOut",
    # Documents
    "DocumentTemplateOut",
    "DocumentBase",
    "DocumentCreate",
    "DocumentUpdate",
    "DocumentOut",
]

