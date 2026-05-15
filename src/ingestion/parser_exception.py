"""
Module pour définir les exceptions des parsers.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Type, Collection

import i18n

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
        return i18n.t(
            "ingestion.parser_exception.error_parser_identification", file=self.file
        )


@dataclass(frozen=True)
class MultipleParsersError(Exception):
    """
    Exception pour les erreurs de multiples parsers.
    """

    parsers: Collection[Type[DataParserABC]]
    """Liste des parsers trouvés."""

    def __str__(self) -> str:
        return i18n.t(
            "ingestion.parser_exception.error_multiple_parsers", parsers=self.parsers
        )
