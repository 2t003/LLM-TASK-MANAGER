"""
Fixtures partagées pour la suite de tests.

Utilise une base SQLite en mémoire pour chaque session de tests,
garantissant l'isolation et la rapidité d'exécution.
"""

from __future__ import annotations

from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.models.domain import (
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


# ---------------------------------------------------------------------------
# Engine & session de test (SQLite in-memory, StaticPool pour partager la connexion)
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite://"  # In-memory SQLite

_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)


@pytest.fixture(autouse=True)
def _setup_db() -> Generator[None, None, None]:
    """Crée les tables avant chaque test et les supprime après."""
    SQLModel.metadata.create_all(bind=_engine)
    yield
    SQLModel.metadata.drop_all(bind=_engine)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    """Fournit une session DB de test avec rollback automatique."""
    with Session(_engine) as session:
        yield session


# ---------------------------------------------------------------------------
# Fixtures d'entités pré-créées (helpers)
# ---------------------------------------------------------------------------


@pytest.fixture()
def project(db: Session) -> Project:
    """Crée un projet de test."""
    p = Project(name="Projet Test", description="Description du projet")
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@pytest.fixture()
def epic(db: Session, project: Project) -> Epic:
    """Crée un epic rattaché au projet de test."""
    e = Epic(project_id=project.id, title="Epic Test", status=EpicStatus.BACKLOG)
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


@pytest.fixture()
def story(db: Session, project: Project) -> Story:
    """Crée une story en statut backlog."""
    s = Story(
        project_id=project.id,
        title="Story Test",
        status=StoryStatus.BACKLOG,
        priority=StoryPriority.MEDIUM,
        story_points=3,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@pytest.fixture()
def sprint(db: Session, project: Project) -> Sprint:
    """Crée un sprint en statut planned."""
    sp = Sprint(
        project_id=project.id,
        name="Sprint 1",
        status=SprintStatus.PLANNED,
    )
    db.add(sp)
    db.commit()
    db.refresh(sp)
    return sp


# ---------------------------------------------------------------------------
# Client HTTP de test (FastAPI TestClient)
# ---------------------------------------------------------------------------


@pytest.fixture()
def client(db: Session) -> Generator[TestClient, None, None]:
    """
    Client HTTP utilisant la DB de test.

    Surcharge la dépendance ``get_db_session`` de FastAPI pour
    pointer vers la session SQLite in-memory.
    """
    from app.db import get_db_session
    from app.main import app

    def _override_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db_session] = _override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
