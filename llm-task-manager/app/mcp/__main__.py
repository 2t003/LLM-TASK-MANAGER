"""
Point d'entrée pour ``python -m app.mcp``.

Permet de lancer le serveur MCP en transport stdio
sans déclencher le double-import (RuntimeWarning) qui survient
lorsqu'on exécute ``python -m app.mcp.server``.
"""

from app.mcp.server import main

main()
