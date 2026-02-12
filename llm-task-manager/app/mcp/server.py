"""
Serveur MCP pour LLM Task Manager.

Expose des tools parallèles aux endpoints REST pour permettre à un LLM
de créer/lire/modifier des projets, epics, stories, sprints, commentaires
et documents directement depuis une conversation (cf. ARCHITECTURE.md).

Usage (local, via transport stdio) :

    python -m app.mcp
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from mcp.server.fastmcp import FastMCP
from sqlmodel import Session, select

from app.db import engine
from app.models import (
    Comment,
    CommentTargetType,
    Document,
    DocumentTemplate,
    Epic,
    Project,
    Sprint,
    Story,
    StoryDescription,
    StoryPriority,
    StoryStatus,
    schemas as sch,
)
from app.models.domain import SprintStatus
from app.services import DomainError
from app.services import sprints as sprint_service
from app.services import stories as story_service


server = FastMCP("llm-task-manager", json_response=True)


def _session() -> Session:
    """Crée une session SQLModel éphémère."""
    return Session(engine)


def _handle_domain_error(exc: DomainError) -> None:
    """
    Convertit une DomainError en exception MCP générique.

    Le client MCP affichera le message au LLM.
    """
    raise RuntimeError(f"{exc.code}: {exc.message}")  # pragma: no cover - glue


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


@server.tool()
async def create_project(name: str, description: Optional[str] = None) -> Dict[str, Any]:
    """Crée un nouveau projet."""
    payload = sch.ProjectCreate(name=name, description=description)
    with _session() as db:
        project = Project(name=payload.name, description=payload.description)
        db.add(project)
        db.commit()
        db.refresh(project)
        return sch.ProjectOut.model_validate(project).model_dump()


@server.tool()
async def list_projects() -> List[Dict[str, Any]]:
    """Liste tous les projets disponibles."""
    with _session() as db:
        results = db.exec(select(Project).order_by(Project.created_at.desc())).all()
        return [sch.ProjectOut.model_validate(p).model_dump() for p in results]


# ---------------------------------------------------------------------------
# Epics
# ---------------------------------------------------------------------------


@server.tool()
async def create_epic(project_id: str, title: str) -> Dict[str, Any]:
    """Crée un epic dans un projet donné."""
    payload = sch.EpicCreate(project_id=UUID(project_id), title=title)
    with _session() as db:
        epic = Epic(project_id=payload.project_id, title=payload.title, status=payload.status)
        db.add(epic)
        db.commit()
        db.refresh(epic)
        return sch.EpicOut.model_validate(epic).model_dump()


@server.tool()
async def get_epic(epic_id: str) -> Dict[str, Any]:
    """Récupère un epic par son identifiant."""
    with _session() as db:
        epic = db.get(Epic, UUID(epic_id))
        if not epic:
            raise RuntimeError("EPIC_NOT_FOUND: Epic not found")
        return sch.EpicOut.model_validate(epic).model_dump()


@server.tool()
async def update_epic(epic_id: str, title: Optional[str] = None, status: Optional[str] = None) -> Dict[str, Any]:
    """
    Met à jour un epic (titre et/ou statut).

    - status doit être une valeur de EpicStatus.
    """
    data: Dict[str, Any] = {}
    if title is not None:
        data["title"] = title
    if status is not None:
        data["status"] = status

    payload = sch.EpicUpdate(**data)
    with _session() as db:
        epic = db.get(Epic, UUID(epic_id))
        if not epic:
            raise RuntimeError("EPIC_NOT_FOUND: Epic not found")

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(epic, field, value)

        db.add(epic)
        db.commit()
        db.refresh(epic)
        return sch.EpicOut.model_validate(epic).model_dump()


@server.tool()
async def list_epics(project_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Liste les epics, optionnellement filtrés par projet."""
    with _session() as db:
        stmt = select(Epic)
        if project_id:
            stmt = stmt.where(Epic.project_id == UUID(project_id))
        stmt = stmt.order_by(Epic.created_at.desc())
        results = db.exec(stmt).all()
        return [sch.EpicOut.model_validate(e).model_dump() for e in results]


@server.tool()
async def search_epics(q: str) -> List[Dict[str, Any]]:
    """Recherche d'epics par mot-clé dans le titre."""
    with _session() as db:
        stmt = select(Epic).where(Epic.title.ilike(f"%{q}%")).order_by(Epic.created_at.desc())
        results = db.exec(stmt).all()
        return [sch.EpicOut.model_validate(e).model_dump() for e in results]


# ---------------------------------------------------------------------------
# Stories
# ---------------------------------------------------------------------------


@server.tool()
async def create_story(
    project_id: str,
    title: str,
    epic_id: Optional[str] = None,
    status: str = StoryStatus.BACKLOG.value,
    priority: str = StoryPriority.MEDIUM.value,
    story_points: int = 0,
    assignee: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Crée une story dans un projet (optionnellement liée à un epic).

    - status : backlog, todo, in_progress, in_review, done
    - priority : low, medium, high, critical
    - story_points : 0,1,2,3,5,8,13
    """
    payload = sch.StoryCreate(
        project_id=UUID(project_id),
        epic_id=UUID(epic_id) if epic_id else None,
        title=title,
        status=StoryStatus(status),
        priority=StoryPriority(priority),
        story_points=story_points,
        assignee=assignee,
    )
    with _session() as db:
        try:
            story = story_service.create_story(db, payload)
        except DomainError as exc:
            _handle_domain_error(exc)
        return sch.StoryOut.model_validate(story).model_dump()


@server.tool()
async def get_story(story_id: str) -> Dict[str, Any]:
    """Récupère une story par son identifiant."""
    with _session() as db:
        story = db.get(Story, UUID(story_id))
        if not story:
            raise RuntimeError("STORY_NOT_FOUND: Story not found")
        return sch.StoryOut.model_validate(story).model_dump()


@server.tool()
async def update_story(
    story_id: str,
    title: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    story_points: Optional[int] = None,
    assignee: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Met à jour une story (titre, statut, priorité, points, assignee).
    Applique les règles métier de transition de statut et de story points.
    """
    data: Dict[str, Any] = {}
    if title is not None:
        data["title"] = title
    if status is not None:
        data["status"] = StoryStatus(status)
    if priority is not None:
        data["priority"] = StoryPriority(priority)
    if story_points is not None:
        data["story_points"] = story_points
    if assignee is not None:
        data["assignee"] = assignee

    payload = sch.StoryUpdate(**data)
    with _session() as db:
        try:
            story = story_service.update_story(db, UUID(story_id), payload)
        except DomainError as exc:
            _handle_domain_error(exc)
        return sch.StoryOut.model_validate(story).model_dump()


@server.tool()
async def list_stories(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assignee: Optional[str] = None,
    sprint_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Liste les stories avec filtres optionnels :
    - status
    - priority
    - assignee
    - sprint_id
    """
    from app.models import StorySprintHistory  # import local pour éviter cycles

    with _session() as db:
        stmt = select(Story)
        if status:
            stmt = stmt.where(Story.status == StoryStatus(status))
        if priority:
            stmt = stmt.where(Story.priority == StoryPriority(priority))
        if assignee:
            stmt = stmt.where(Story.assignee == assignee)
        if sprint_id:
            stmt = (
                stmt.join(StorySprintHistory)
                .where(
                    StorySprintHistory.sprint_id == UUID(sprint_id),
                    StorySprintHistory.is_active.is_(True),
                )
            )
        stmt = stmt.order_by(Story.created_at.desc())
        results = db.exec(stmt).all()
        return [sch.StoryOut.model_validate(s).model_dump() for s in results]


@server.tool()
async def search_stories(q: str) -> List[Dict[str, Any]]:
    """Recherche de stories par mot-clé dans le titre."""
    with _session() as db:
        stmt = select(Story).where(Story.title.ilike(f"%{q}%")).order_by(Story.created_at.desc())
        results = db.exec(stmt).all()
        return [sch.StoryOut.model_validate(s).model_dump() for s in results]


# ---------------------------------------------------------------------------
# Story Descriptions
# ---------------------------------------------------------------------------


@server.tool()
async def create_story_description(
    story_id: str,
    description: str,
    acceptance_criteria: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Crée une description détaillée pour une story.
    Chaque story ne peut avoir qu'une seule description.
    """
    payload = sch.StoryDescriptionCreate(
        story_id=UUID(story_id),
        description=description,
        acceptance_criteria=acceptance_criteria,
    )
    with _session() as db:
        story = db.get(Story, payload.story_id)
        if not story:
            raise RuntimeError("STORY_NOT_FOUND: Story not found")

        existing = db.exec(
            select(StoryDescription).where(StoryDescription.story_id == payload.story_id)
        ).first()
        if existing:
            raise RuntimeError(
                "DESCRIPTION_EXISTS: A description already exists for this story. Use update_story_description instead."
            )

        desc = StoryDescription(
            story_id=payload.story_id,
            description=payload.description,
            acceptance_criteria=payload.acceptance_criteria,
        )
        db.add(desc)
        db.commit()
        db.refresh(desc)
        return sch.StoryDescriptionOut.model_validate(desc).model_dump()


@server.tool()
async def get_story_description(story_id: str) -> Dict[str, Any]:
    """Récupère la description d'une story par l'identifiant de la story."""
    with _session() as db:
        desc = db.exec(
            select(StoryDescription).where(StoryDescription.story_id == UUID(story_id))
        ).first()
        if not desc:
            raise RuntimeError("DESCRIPTION_NOT_FOUND: No description found for this story")
        return sch.StoryDescriptionOut.model_validate(desc).model_dump()


@server.tool()
async def update_story_description(
    story_id: str,
    description: Optional[str] = None,
    acceptance_criteria: Optional[str] = None,
) -> Dict[str, Any]:
    """Met à jour la description d'une story (description et/ou critères d'acceptation)."""
    data: Dict[str, Any] = {}
    if description is not None:
        data["description"] = description
    if acceptance_criteria is not None:
        data["acceptance_criteria"] = acceptance_criteria

    payload = sch.StoryDescriptionUpdate(**data)
    with _session() as db:
        desc = db.exec(
            select(StoryDescription).where(StoryDescription.story_id == UUID(story_id))
        ).first()
        if not desc:
            raise RuntimeError("DESCRIPTION_NOT_FOUND: No description found for this story")

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(desc, field, value)

        db.add(desc)
        db.commit()
        db.refresh(desc)
        return sch.StoryDescriptionOut.model_validate(desc).model_dump()


@server.tool()
async def delete_story_description(story_id: str) -> Dict[str, str]:
    """Supprime la description d'une story."""
    with _session() as db:
        desc = db.exec(
            select(StoryDescription).where(StoryDescription.story_id == UUID(story_id))
        ).first()
        if not desc:
            raise RuntimeError("DESCRIPTION_NOT_FOUND: No description found for this story")
        db.delete(desc)
        db.commit()
        return {"status": "deleted", "story_id": story_id}


# ---------------------------------------------------------------------------
# Sprints
# ---------------------------------------------------------------------------


@server.tool()
async def create_sprint(
    project_id: str,
    name: str,
    status: str = SprintStatus.PLANNED.value,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Crée un sprint pour un projet.
    Les dates doivent être au format ISO (YYYY-MM-DD) si fournies.
    """
    payload = sch.SprintCreate(
        project_id=UUID(project_id),
        name=name,
        status=SprintStatus(status),
        start_date=start_date,  # Pydantic gère la conversion date
        end_date=end_date,
    )
    with _session() as db:
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
        return sch.SprintOut.model_validate(sprint).model_dump()


@server.tool()
async def start_sprint(sprint_id: str) -> Dict[str, Any]:
    """Démarre un sprint (passe le statut à ACTIVE)."""
    with _session() as db:
        try:
            sprint = sprint_service.start_sprint(db, UUID(sprint_id))
        except DomainError as exc:
            _handle_domain_error(exc)
        return sch.SprintOut.model_validate(sprint).model_dump()


@server.tool()
async def close_sprint(sprint_id: str) -> Dict[str, Any]:
    """
    Clôture un sprint, uniquement si toutes les stories associées sont en `done`.
    """
    with _session() as db:
        try:
            sprint = sprint_service.close_sprint(db, UUID(sprint_id))
        except DomainError as exc:
            _handle_domain_error(exc)
        return sch.SprintOut.model_validate(sprint).model_dump()


@server.tool()
async def list_sprints(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Liste les sprints avec filtres optionnels par projet et statut."""
    with _session() as db:
        stmt = select(Sprint)
        if project_id:
            stmt = stmt.where(Sprint.project_id == UUID(project_id))
        if status:
            stmt = stmt.where(Sprint.status == SprintStatus(status))
        stmt = stmt.order_by(Sprint.created_at.desc())
        results = db.exec(stmt).all()
        return [sch.SprintOut.model_validate(s).model_dump() for s in results]


@server.tool()
async def add_story_to_sprint(sprint_id: str, story_id: str) -> Dict[str, Any]:
    """Ajoute une story à un sprint (en tant que story active)."""
    with _session() as db:
        try:
            sprint_service.add_story_to_sprint(db, UUID(sprint_id), UUID(story_id))
            db_sprint = db.get(Sprint, UUID(sprint_id))
        except DomainError as exc:
            _handle_domain_error(exc)
        return sch.SprintOut.model_validate(db_sprint).model_dump()


@server.tool()
async def remove_story_from_sprint(sprint_id: str, story_id: str) -> Dict[str, Any]:
    """Retire une story du sprint (désactive le lien actif)."""
    with _session() as db:
        try:
            sprint_service.remove_story_from_sprint(db, UUID(sprint_id), UUID(story_id))
            db_sprint = db.get(Sprint, UUID(sprint_id))
        except DomainError as exc:
            _handle_domain_error(exc)
        return sch.SprintOut.model_validate(db_sprint).model_dump()


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


@server.tool()
async def add_comment(
    project_id: str,
    target_type: str,
    target_id: str,
    content: str,
) -> Dict[str, Any]:
    """Ajoute un commentaire sur une story ou un epic."""
    payload = sch.CommentCreate(
        project_id=UUID(project_id),
        target_type=CommentTargetType(target_type),
        target_id=UUID(target_id),
        content=content,
    )
    with _session() as db:
        comment = Comment(
            project_id=payload.project_id,
            target_type=payload.target_type,
            target_id=payload.target_id,
            content=payload.content,
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)
        return sch.CommentOut.model_validate(comment).model_dump()


@server.tool()
async def list_comments(
    project_id: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Liste les commentaires, éventuellement filtrés par projet et cible."""
    with _session() as db:
        stmt = select(Comment)
        if project_id:
            stmt = stmt.where(Comment.project_id == UUID(project_id))
        if target_type:
            stmt = stmt.where(Comment.target_type == CommentTargetType(target_type))
        if target_id:
            stmt = stmt.where(Comment.target_id == UUID(target_id))

        stmt = stmt.order_by(Comment.created_at.desc())
        results = db.exec(stmt).all()
        return [sch.CommentOut.model_validate(c).model_dump() for c in results]


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


@server.tool()
async def create_document(
    project_id: str,
    title: str,
    content: Optional[str] = None,
    template_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Crée un document, vide ou basé sur un template prédéfini.
    Si `content` est vide et `template_key` fourni, le contenu du template est utilisé.
    """
    payload = sch.DocumentCreate(
        project_id=UUID(project_id),
        title=title,
        content=content or "",
        template_key=template_key,
    )
    with _session() as db:
        effective_content = payload.content
        if not effective_content and payload.template_key:
            tmpl = db.get(DocumentTemplate, payload.template_key)
            effective_content = tmpl.content if tmpl else ""

        doc = Document(
            project_id=payload.project_id,
            title=payload.title,
            content=effective_content,
            template_key=payload.template_key,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return sch.DocumentOut.model_validate(doc).model_dump()


@server.tool()
async def get_document(document_id: str) -> Dict[str, Any]:
    """Récupère un document par son identifiant."""
    with _session() as db:
        doc = db.get(Document, UUID(document_id))
        if not doc:
            raise RuntimeError("DOCUMENT_NOT_FOUND: Document not found")
        return sch.DocumentOut.model_validate(doc).model_dump()


@server.tool()
async def update_document(
    document_id: str,
    title: Optional[str] = None,
    content: Optional[str] = None,
    template_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Met à jour un document (titre, contenu, clé de template)."""
    data: Dict[str, Any] = {}
    if title is not None:
        data["title"] = title
    if content is not None:
        data["content"] = content
    if template_key is not None:
        data["template_key"] = template_key

    payload = sch.DocumentUpdate(**data)
    with _session() as db:
        doc = db.get(Document, UUID(document_id))
        if not doc:
            raise RuntimeError("DOCUMENT_NOT_FOUND: Document not found")

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(doc, field, value)

        db.add(doc)
        db.commit()
        db.refresh(doc)
        return sch.DocumentOut.model_validate(doc).model_dump()


@server.tool()
async def list_documents(
    project_id: Optional[str] = None,
    template_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Liste les documents, filtrables par projet et template."""
    with _session() as db:
        stmt = select(Document)
        if project_id:
            stmt = stmt.where(Document.project_id == UUID(project_id))
        if template_key:
            stmt = stmt.where(Document.template_key == template_key)
        stmt = stmt.order_by(Document.created_at.desc())
        results = db.exec(stmt).all()
        return [sch.DocumentOut.model_validate(d).model_dump() for d in results]


@server.tool()
async def search_documents(q: str) -> List[Dict[str, Any]]:
    """Recherche de documents par mot-clé dans le titre."""
    with _session() as db:
        stmt = select(Document).where(Document.title.ilike(f"%{q}%")).order_by(
            Document.created_at.desc()
        )
        results = db.exec(stmt).all()
        return [sch.DocumentOut.model_validate(d).model_dump() for d in results]


# ---------------------------------------------------------------------------
# Entrée stdio pour MCP
# ---------------------------------------------------------------------------


def main() -> None:  # pragma: no cover - point d'entrée
    """Point d'entrée du serveur MCP (transport stdio)."""
    # Utilise le transport stdio recommandé par la doc du SDK MCP.
    server.run(transport="stdio")


if __name__ == "__main__":  # pragma: no cover
    main()

