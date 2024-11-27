"""
Module pour les exceptions des stations.

Ce module contient la classe StationsError pour les erreurs des stations.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class StationsError(Exception):
    """
    Classe pour les erreurs des stations.

    :param message: Message de l'erreur.
    :type message: str
    :param error: Erreur de l'erreur.
    :type error: str
    :param status_code: Code de statut de l'erreur.
    :type status_code: int
    """

    message: str
    """Message de l'erreur."""
    error: str
    """Erreur de l'erreur."""
    status_code: int
    """Code de statut de l'erreur."""

    def __str__(self) -> str:
        return f"StationError: {self.message} - {self.error} (Status code: {self.status_code})"
