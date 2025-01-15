"""
Module permettant de définir les modèles de données utilisés par les parsers.

Ce module contient les classes permettant de définir les modèles de données utilisés par les parsers.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Type

from . import parser_ids as ids
from .parser_exception import MultipleParsersError, DataParserABC

class DataType(StrEnum):
    """
    Enumération des types de données.
    """

    OFM: str = ids.OFM
    """Type de données OFM."""
    DCDB: str = ids.DCDB
    """Type de données DCDB."""
    LOWRANCE: str = ids.LOWRANCE
    """Type de données Lowrance."""
    ACTISENSE: str = ids.ACTISENSE
    """Type de données Actisense."""
    BLACKBOX: str = ids.BLACKBOX
    """Type de données BlackBox."""


@dataclass
class ParserFiles:
    """
    Classe permettant de stocker les fichiers et le parser associés.

    :param parser: Le parser associé aux fichiers.
    :type parser: Type[DataParserABC]
    :param files: Les fichiers à traiter.
    :type files: list[Path]
    """

    parser: Type[DataParserABC] = None
    """Le parser associé aux fichiers."""
    files: list[Path] = field(default_factory=list)
    """Les fichiers à traiter."""
    data_file_type = None

    def __setattr__(self, name, value):
        if name == "parser" and self.parser is not None and self.parser != value:
            raise MultipleParsersError(parsers=(self.parser, value))

        super().__setattr__(name, value)