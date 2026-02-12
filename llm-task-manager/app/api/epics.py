"""
Routes REST pour les epics.

Endpoints (cf. ARCHITECTURE.md) :
- POST /v1/epics
- GET  /v1/epics/{epic_id}
- PATCH /v1/epics/{epic_id}
- GET  /v1/epics
- GET  /v1/epics/search
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.db import get_db_session
from app.models import Epic
from app.models import schemas as sch


router = APIRouter(prefix="/epics", tags=["epics"])


@router.post(
    "",
    response_model=sch.EpicOut,
    status_code=status.HTTP_201_CREATED,
)
def create_epic(
    payload: sch.EpicCreate,
    db: Session = Depends(get_db_session),
) -> sch.EpicOut:
    epic = Epic(
        project_id=payload.project_id,
        title=payload.title,
        status=payload.status,
    )
    db.add(epic)
    db.commit()
    db.refresh(epic)
    return sch.EpicOut.model_validate(epic)


@router.get(
    "/{epic_id}",
    response_model=sch.EpicOut,
)
def get_epic(
    epic_id: UUID,
    db: Session = Depends(get_db_session),
) -> sch.EpicOut:
    epic = db.get(Epic, epic_id)
    if not epic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Epic not found")
    return sch.EpicOut.model_validate(epic)


@router.patch(
    "/{epic_id}",
    response_model=sch.EpicOut,
)
def update_epic(
    epic_id: UUID,
    payload: sch.EpicUpdate,
    db: Session = Depends(get_db_session),
) -> sch.EpicOut:
    epic = db.get(Epic, epic_id)
    if not epic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Epic not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(epic, field, value)

    db.add(epic)
    db.commit()
    db.refresh(epic)
    return sch.EpicOut.model_validate(epic)


@router.get(
    "",
    response_model=List[sch.EpicOut],
)
def list_epics(
    project_id: Optional[UUID] = Query(default=None),
    db: Session = Depends(get_db_session),
) -> list[sch.EpicOut]:
    """Liste les epics, éventuellement filtrés par projet."""
    stmt = select(Epic)
    if project_id:
        stmt = stmt.where(Epic.project_id == project_id)
    stmt = stmt.order_by(Epic.created_at.desc())
    results = db.exec(stmt).all()
    return [sch.EpicOut.model_validate(e) for e in results]


@router.get(
    "/search",
    response_model=List[sch.EpicOut],
)
def search_epics(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db_session),
) -> list[sch.EpicOut]:
    """Recherche d'epics par mot-clé dans le titre."""
    stmt = select(Epic).where(Epic.title.ilike(f"%{q}%")).order_by(Epic.created_at.desc())
    results = db.exec(stmt).all()
    return [sch.EpicOut.model_validate(e) for e in results]


