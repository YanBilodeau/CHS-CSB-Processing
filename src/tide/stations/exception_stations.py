"""
Module pour les exceptions des stations.

Ce module contient la classe StationsError pour les erreurs des stations.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class StationsError(Exception):
    """
    Classe pour les erreurs des stations.

    message: (str) Message de l'erreur.
    error: (str) Erreur de l'erreur.
    status_code: (int) Code de statut de l'erreur.
    """

    message: str
    error: str
    status_code: int

    def __str__(self) -> str:
        return f"StationError: {self.message} - {self.error} (Status code: {self.status_code})"
