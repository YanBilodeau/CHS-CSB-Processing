"""
Module pour définir les exceptions des parsers.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Type, Collection

from .parser_abc import DataParserABC


@dataclass(frozen=True)
class ParserIdentifierError(Exception):
    """
    Exception pour les erreurs d'identification du parser.

    :param file: (Path) Le fichier en cours de lecture.
    """

    file: Path
    """Le fichier en erreur."""

    def __str__(self) -> str:
        return (
            f"Erreur lors de l'idendification du parser pour le fichier : {self.file}."
        )


@dataclass(frozen=True)
class MultipleParsersError(Exception):
    """
    Exception pour les erreurs de multiples parsers.
    """

    parsers: Collection[Type[DataParserABC]]
    """Liste des parsers trouvés."""

    def __str__(self) -> str:
        return f"Plus d'un type de parser a été identifié pour les fichiers : {self.parsers}"
