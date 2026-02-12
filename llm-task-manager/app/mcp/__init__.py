"""
Couche MCP : définition des tools exposés au LLM.

Les tools sont implémentés dans `server.py` via le SDK Python MCP
et réutilisent la même logique métier que les routes REST.

Lancement recommandé : ``python -m app.mcp`` (utilise __main__.py).
"""


def __getattr__(name: str):  # noqa: N807
    """Import paresseux pour éviter le double-import avec ``python -m``."""
    if name in ("server", "main"):
        from .server import server, main  # noqa: F811

        globals()["server"] = server
        globals()["main"] = main
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["server", "main"]

