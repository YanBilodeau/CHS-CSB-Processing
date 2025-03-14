"""
Module pour définir les exceptions du parsing.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Type


@dataclass(frozen=True)
class ParsingError(Exception):
    """
    Classe de base pour les exceptions de parsing.

    :param file: (Path) Le fichier en cours de lecture.
    :param column: (str) Le nom de la colonne en erreur.
    """

    file: Path
    """Le ficher en erreur."""
    column: str
    """Le nom de la colonne en erreur."""

    def __str__(self) -> str:
        return f"Erreur lors de la lecture du fichier : {self.file}. Le fichier n'a pas de colonne '{self.column}'."


@dataclass(frozen=True)
class ParsingDataframeTimeError(ParsingError):
    """
    Exception pour les erreurs de parsing de la colonne de temps.
    """

    pass


@dataclass(frozen=True)
class ParsingDataframeDepthError(ParsingError):
    """
    Exception pour les erreurs de parsing de la colonne de profondeur.
    """

    pass


@dataclass(frozen=True)
class ParsingDataframeLongitudeError(ParsingError):
    """
    Exception pour les erreurs de parsing de la colonne de longitude
    """

    pass


@dataclass(frozen=True)
class ParsingDataframeLatitudeError(ParsingError):
    """
    Exception pour les erreurs de parsing de la colonne de latitude.
    """

    pass


@dataclass(frozen=True)
class ColumnException:
    """
    Classe pour les exceptions de colonnes.

    :param column_name: (str) Le nom de la colonne.
    :param error: (Type[ParsingError]) L'erreur de parsing associée.
    """

    column_name: str
    """Le nom de la colonne."""
    error: Type[ParsingError]
    """L'erreur de parsing associée."""
