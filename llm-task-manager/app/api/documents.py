"""
Routes REST pour les documents.

Endpoints (cf. ARCHITECTURE.md) :
- POST /v1/documents
- GET  /v1/documents/{document_id}
- PATCH /v1/documents/{document_id}
- GET  /v1/documents
- GET  /v1/documents/search
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.db import get_db_session
from app.models import Document, DocumentTemplate
from app.models import schemas as sch


router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "",
    response_model=sch.DocumentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_document(
    payload: sch.DocumentCreate,
    db: Session = Depends(get_db_session),
) -> sch.DocumentOut:
    # Si un template_key est fourni, on peut charger le contenu par défaut
    content = payload.content
    if not content and payload.template_key:
        tmpl = db.get(DocumentTemplate, payload.template_key)
        content = tmpl.content if tmpl else ""

    doc = Document(
        project_id=payload.project_id,
        title=payload.title,
        content=content,
        template_key=payload.template_key,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return sch.DocumentOut.model_validate(doc)


@router.get(
    "/{document_id}",
    response_model=sch.DocumentOut,
)
def get_document(
    document_id: UUID,
    db: Session = Depends(get_db_session),
) -> sch.DocumentOut:
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return sch.DocumentOut.model_validate(doc)


@router.patch(
    "/{document_id}",
    response_model=sch.DocumentOut,
)
def update_document(
    document_id: UUID,
    payload: sch.DocumentUpdate,
    db: Session = Depends(get_db_session),
) -> sch.DocumentOut:
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(doc, field, value)

    db.add(doc)
    db.commit()
    db.refresh(doc)
    return sch.DocumentOut.model_validate(doc)


@router.get(
    "",
    response_model=List[sch.DocumentOut],
)
def list_documents(
    project_id: Optional[UUID] = Query(default=None),
    template_key: Optional[str] = Query(default=None),
    db: Session = Depends(get_db_session),
) -> list[sch.DocumentOut]:
    """Liste les documents, avec filtres par projet et template."""
    stmt = select(Document)
    if project_id:
        stmt = stmt.where(Document.project_id == project_id)
    if template_key:
        stmt = stmt.where(Document.template_key == template_key)
    stmt = stmt.order_by(Document.created_at.desc())
    results = db.exec(stmt).all()
    return [sch.DocumentOut.model_validate(d) for d in results]


@router.get(
    "/search",
    response_model=List[sch.DocumentOut],
)
def search_documents(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db_session),
) -> list[sch.DocumentOut]:
    """Recherche de documents par mot-clé dans le titre."""
    stmt = select(Document).where(Document.title.ilike(f"%{q}%")).order_by(
        Document.created_at.desc()
    )
    results = db.exec(stmt).all()
    return [sch.DocumentOut.model_validate(d) for d in results]


