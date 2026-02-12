"""
Routes REST pour les stories.

Endpoints (cf. ARCHITECTURE.md) :
- POST /v1/stories
- GET  /v1/stories/{story_id}
- PATCH /v1/stories/{story_id}
- GET  /v1/stories
- GET  /v1/stories/search
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.db import get_db_session
from app.models import Story
from app.models import schemas as sch
from app.models.domain import StoryPriority, StoryStatus
from app.services import DomainError
from app.services import stories as story_service


router = APIRouter(prefix="/stories", tags=["stories"])


@router.post(
    "",
    response_model=sch.StoryOut,
    status_code=status.HTTP_201_CREATED,
)
def create_story(
    payload: sch.StoryCreate,
    db: Session = Depends(get_db_session),
) -> sch.StoryOut:
    try:
        story = story_service.create_story(db, payload)
    except DomainError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return sch.StoryOut.model_validate(story)


@router.get(
    "/{story_id}",
    response_model=sch.StoryOut,
)
def get_story(
    story_id: UUID,
    db: Session = Depends(get_db_session),
) -> sch.StoryOut:
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")
    return sch.StoryOut.model_validate(story)


@router.patch(
    "/{story_id}",
    response_model=sch.StoryOut,
)
def update_story(
    story_id: UUID,
    payload: sch.StoryUpdate,
    db: Session = Depends(get_db_session),
) -> sch.StoryOut:
    try:
        story = story_service.update_story(db, story_id, payload)
    except DomainError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return sch.StoryOut.model_validate(story)


@router.get(
    "",
    response_model=List[sch.StoryOut],
)
def list_stories(
    status_filter: Optional[StoryStatus] = Query(default=None, alias="status"),
    priority_filter: Optional[StoryPriority] = Query(default=None, alias="priority"),
    assignee: Optional[str] = Query(default=None),
    sprint_id: Optional[UUID] = Query(default=None),
    db: Session = Depends(get_db_session),
) -> list[sch.StoryOut]:
    """
    Liste les stories avec filtres :
    - status
    - priority
    - assignee
    - sprint_id (via StorySprintHistory.is_active)
    """
    from app.models import StorySprintHistory  # import local pour éviter cycles

    stmt = select(Story)

    if status_filter:
        stmt = stmt.where(Story.status == status_filter)
    if priority_filter:
        stmt = stmt.where(Story.priority == priority_filter)
    if assignee:
        stmt = stmt.where(Story.assignee == assignee)
    if sprint_id:
        stmt = (
            stmt.join(StorySprintHistory)
            .where(
                StorySprintHistory.sprint_id == sprint_id,
                StorySprintHistory.is_active.is_(True),
            )
        )

    stmt = stmt.order_by(Story.created_at.desc())
    results = db.exec(stmt).all()
    return [sch.StoryOut.model_validate(s) for s in results]


@router.get(
    "/search",
    response_model=List[sch.StoryOut],
)
def search_stories(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db_session),
) -> list[sch.StoryOut]:
    """Recherche de stories par mot-clé dans le titre."""
    stmt = select(Story).where(Story.title.ilike(f"%{q}%")).order_by(Story.created_at.desc())
    results = db.exec(stmt).all()
    return [sch.StoryOut.model_validate(s) for s in results]


