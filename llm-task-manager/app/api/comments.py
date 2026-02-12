"""
Routes REST pour les commentaires.

Endpoints (cf. ARCHITECTURE.md) :
- POST /v1/comments
- GET  /v1/comments
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session, select

from app.db import get_db_session
from app.models import Comment
from app.models import schemas as sch
from app.models.domain import CommentTargetType


router = APIRouter(prefix="/comments", tags=["comments"])


@router.post(
    "",
    response_model=sch.CommentOut,
    status_code=status.HTTP_201_CREATED,
)
def add_comment(
    payload: sch.CommentCreate,
    db: Session = Depends(get_db_session),
) -> sch.CommentOut:
    comment = Comment(
        project_id=payload.project_id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        content=payload.content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return sch.CommentOut.model_validate(comment)


@router.get(
    "",
    response_model=List[sch.CommentOut],
)
def list_comments(
    project_id: Optional[str] = Query(default=None),
    target_type: Optional[CommentTargetType] = Query(default=None),
    target_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db_session),
) -> list[sch.CommentOut]:
    """
    Liste les commentaires, avec filtres optionnels :
    - project_id
    - target_type (epic/story)
    - target_id
    """
    stmt = select(Comment)
    if project_id:
        stmt = stmt.where(Comment.project_id == project_id)
    if target_type:
        stmt = stmt.where(Comment.target_type == target_type)
    if target_id:
        stmt = stmt.where(Comment.target_id == target_id)

    stmt = stmt.order_by(Comment.created_at.desc())
    results = db.exec(stmt).all()
    return [sch.CommentOut.model_validate(c) for c in results]


