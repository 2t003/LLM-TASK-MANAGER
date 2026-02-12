"""
Routes REST pour les projets.

Endpoints (cf. ARCHITECTURE.md) :
- POST /v1/projects
- GET  /v1/projects
"""

from typing import List

from fastapi import APIRouter, Depends, status
from sqlmodel import Session, select

from app.db import get_db_session
from app.models import Project
from app.models import schemas as sch


router = APIRouter(prefix="/projects", tags=["projects"])


@router.post(
    "",
    response_model=sch.ProjectOut,
    status_code=status.HTTP_201_CREATED,
)
def create_project(
    payload: sch.ProjectCreate,
    db: Session = Depends(get_db_session),
) -> sch.ProjectOut:
    """Crée un nouveau projet."""
    project = Project(name=payload.name, description=payload.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return sch.ProjectOut.model_validate(project)


@router.get(
    "",
    response_model=List[sch.ProjectOut],
)
def list_projects(
    db: Session = Depends(get_db_session),
) -> list[sch.ProjectOut]:
    """Liste tous les projets."""
    results = db.exec(select(Project).order_by(Project.created_at.desc())).all()
    return [sch.ProjectOut.model_validate(p) for p in results]


