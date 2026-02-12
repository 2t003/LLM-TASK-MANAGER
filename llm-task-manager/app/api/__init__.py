"""
Couche API REST de LLM Task Manager.

Ce module exposera les routers FastAPI pour les entités :
- projets
- epics
- stories
- sprints
- commentaires
- documents
"""

from fastapi import APIRouter

from app.api import comments, documents, epics, projects, sprints, stories, story_descriptions

router = APIRouter()

# Montage des sous-routers REST
router.include_router(projects.router)
router.include_router(epics.router)
router.include_router(stories.router)
router.include_router(story_descriptions.router)
router.include_router(sprints.router)
router.include_router(comments.router)
router.include_router(documents.router)

