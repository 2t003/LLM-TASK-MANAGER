"""
Package `app.models` : expose les modèles de domaine et les schémas Pydantic.

- `domain`  : modèles ORM (SQLModel) mappés sur la base PostgreSQL
- `schemas` : modèles Pydantic (v2) pour les payloads d'entrée/sortie
"""

from .domain import (  # noqa: F401
    Comment,
    CommentTargetType,
    Document,
    DocumentTemplate,
    Epic,
    EpicStatus,
    Project,
    Sprint,
    SprintStatus,
    Story,
    StoryPriority,
    StorySprintHistory,
    StoryStatus,
)
from . import schemas  # noqa: F401

__all__ = [
    # ORM/domain
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
    # Schemas module
    "schemas",
]



