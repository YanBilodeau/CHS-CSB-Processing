"""
Ce module contient les constantes de configuration du logger.
"""

LOG_FORMAT: str = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: ^8} | {process}:{thread}:{name}:{module}:{function}:{line}:{extra[hostname]}:{extra[username]} - {message}"
)
"""Constante de format de log."""
