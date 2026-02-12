"""
Package principal de l'application LLM Task Manager.

Les sous-modules sont organisés par couches :
- api      : couches REST (routes FastAPI)
- mcp      : tools MCP
- services : logique métier
- models   : modèles Pydantic / ORM
- db       : accès base de données
"""

from .main import create_app  # pragma: no cover

__all__ = ["create_app"]

