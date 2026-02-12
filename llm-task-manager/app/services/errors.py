"""
Exceptions métier pour la couche services.
"""

from dataclasses import dataclass


@dataclass
class DomainError(Exception):
    """
    Erreur métier contrôlée.

    Attributs :
    - code : code symbolique (ex: INVALID_STATUS_TRANSITION)
    - message : message lisible pour l'API/LLM
    - http_status : code HTTP recommandé (400, 404, 409, ...)
    """

    code: str
    message: str
    http_status: int = 400

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.code}: {self.message}"


__all__ = ["DomainError"]

