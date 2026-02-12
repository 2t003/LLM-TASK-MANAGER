"""
Couche services : logique métier de LLM Task Manager.

Cette couche encapsule :
- les règles de workflow des stories
- la gestion des sprints (start/close, affectation)
- l'application des règles métier décrites dans ARCHITECTURE.md
"""

from .errors import DomainError  # noqa: F401
from . import stories, sprints  # noqa: F401

__all__ = ["DomainError", "stories", "sprints"]

