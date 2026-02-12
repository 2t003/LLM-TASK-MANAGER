"""
Routes REST pour les descriptions de user stories.

Endpoints :
- POST   /v1/story-descriptions
- GET    /v1/story-descriptions/{story_id}
- PATCH  /v1/story-descriptions/{story_id}
- DELETE /v1/story-descriptions/{story_id}
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.db import get_db_session
from app.models import Story, StoryDescription
from app.models import schemas as sch


router = APIRouter(prefix="/story-descriptions", tags=["story-descriptions"])


@router.post(
    "",
    response_model=sch.StoryDescriptionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_story_description(
    payload: sch.StoryDescriptionCreate,
    db: Session = Depends(get_db_session),
) -> sch.StoryDescriptionOut:
    # Vérifier que la story existe
    story = db.get(Story, payload.story_id)
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Story not found"
        )

    # Vérifier qu'il n'y a pas déjà une description pour cette story
    existing = db.exec(
        select(StoryDescription).where(StoryDescription.story_id == payload.story_id)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A description already exists for this story. Use PATCH to update it.",
        )

    desc = StoryDescription(
        story_id=payload.story_id,
        description=payload.description,
        acceptance_criteria=payload.acceptance_criteria,
    )
    db.add(desc)
    db.commit()
    db.refresh(desc)
    return sch.StoryDescriptionOut.model_validate(desc)


@router.get(
    "/{story_id}",
    response_model=sch.StoryDescriptionOut,
)
def get_story_description(
    story_id: UUID,
    db: Session = Depends(get_db_session),
) -> sch.StoryDescriptionOut:
    desc = db.exec(
        select(StoryDescription).where(StoryDescription.story_id == story_id)
    ).first()
    if not desc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No description found for this story",
        )
    return sch.StoryDescriptionOut.model_validate(desc)


@router.patch(
    "/{story_id}",
    response_model=sch.StoryDescriptionOut,
)
def update_story_description(
    story_id: UUID,
    payload: sch.StoryDescriptionUpdate,
    db: Session = Depends(get_db_session),
) -> sch.StoryDescriptionOut:
    desc = db.exec(
        select(StoryDescription).where(StoryDescription.story_id == story_id)
    ).first()
    if not desc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No description found for this story",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(desc, field, value)

    db.add(desc)
    db.commit()
    db.refresh(desc)
    return sch.StoryDescriptionOut.model_validate(desc)


@router.delete(
    "/{story_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_story_description(
    story_id: UUID,
    db: Session = Depends(get_db_session),
) -> None:
    desc = db.exec(
        select(StoryDescription).where(StoryDescription.story_id == story_id)
    ).first()
    if not desc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No description found for this story",
        )
    db.delete(desc)
    db.commit()
