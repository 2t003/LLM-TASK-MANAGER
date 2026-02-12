"""
Routes REST pour les sprints.

Endpoints (cf. ARCHITECTURE.md) :
- POST   /v1/sprints
- POST   /v1/sprints/{sprint_id}/start
- POST   /v1/sprints/{sprint_id}/close
- POST   /v1/sprints/{sprint_id}/stories/{story_id}
- DELETE /v1/sprints/{sprint_id}/stories/{story_id}
- GET    /v1/sprints

Les règles métier avancées (ex: clôture seulement si toutes les stories sont `done`)
seront implémentées à l'étape Service Layer.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.db import get_db_session
from app.models import Sprint
from app.models import schemas as sch
from app.models.domain import SprintStatus
from app.services import DomainError
from app.services import sprints as sprint_service


router = APIRouter(prefix="/sprints", tags=["sprints"])


@router.post(
    "",
    response_model=sch.SprintOut,
    status_code=status.HTTP_201_CREATED,
)
def create_sprint(
    payload: sch.SprintCreate,
    db: Session = Depends(get_db_session),
) -> sch.SprintOut:
    sprint = Sprint(
        project_id=payload.project_id,
        name=payload.name,
        status=payload.status,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    db.add(sprint)
    db.commit()
    db.refresh(sprint)
    return sch.SprintOut.model_validate(sprint)


@router.post(
    "/{sprint_id}/start",
    response_model=sch.SprintOut,
)
def start_sprint(
    sprint_id: UUID,
    db: Session = Depends(get_db_session),
) -> sch.SprintOut:
    try:
        sprint = sprint_service.start_sprint(db, sprint_id)
    except DomainError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return sch.SprintOut.model_validate(sprint)


@router.post(
    "/{sprint_id}/close",
    response_model=sch.SprintOut,
)
def close_sprint(
    sprint_id: UUID,
    db: Session = Depends(get_db_session),
) -> sch.SprintOut:
    try:
        sprint = sprint_service.close_sprint(db, sprint_id)
    except DomainError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return sch.SprintOut.model_validate(sprint)


@router.post(
    "/{sprint_id}/stories/{story_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def add_story_to_sprint(
    sprint_id: UUID,
    story_id: UUID,
    db: Session = Depends(get_db_session),
) -> None:
    try:
        sprint_service.add_story_to_sprint(db, sprint_id, story_id)
    except DomainError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


@router.delete(
    "/{sprint_id}/stories/{story_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_story_from_sprint(
    sprint_id: UUID,
    story_id: UUID,
    db: Session = Depends(get_db_session),
) -> None:
    try:
        sprint_service.remove_story_from_sprint(db, sprint_id, story_id)
    except DomainError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


@router.get(
    "",
    response_model=List[sch.SprintOut],
)
def list_sprints(
    project_id: Optional[UUID] = Query(default=None),
    status_filter: Optional[SprintStatus] = Query(default=None, alias="status"),
    db: Session = Depends(get_db_session),
) -> list[sch.SprintOut]:
    """Liste les sprints, avec filtres par projet et statut."""
    stmt = select(Sprint)
    if project_id:
        stmt = stmt.where(Sprint.project_id == project_id)
    if status_filter:
        stmt = stmt.where(Sprint.status == status_filter)
    stmt = stmt.order_by(Sprint.created_at.desc())
    results = db.exec(stmt).all()
    return [sch.SprintOut.model_validate(s) for s in results]


