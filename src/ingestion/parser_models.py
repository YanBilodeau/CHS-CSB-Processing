"""
Module permettant de définir les modèles de données utilisés par les parsers.

Ce module contient les classes permettant de définir les modèles de données utilisés par les parsers.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Type, TypeVar

from . import parser_ids as ids
from .parser_abc import DataParserABC
from .parser_black_box import DataParserBlackBox
from .parser_dcdb import DataParserBCDB
from .parser_lowrance import DataParserLowrance
from .parser_ofm import DataParserOFM
from .parser_exception import MultipleParsersError
from .parser_b12_csb import DataParserB12CSB
from .parser_wibl import DataParserWIBL


class DataLoggerType(StrEnum):
    """
    Enumération des types de données.
    """

    OFM = ids.OFM
    """Type de données OFM."""
    DCDB = ids.DCDB
    """Type de données DCDB."""
    LOWRANCE = ids.LOWRANCE
    """Type de données Lowrance."""
    ACTISENSE = ids.ACTISENSE
    """Type de données Actisense."""
    BLACKBOX = ids.BLACKBOX
    """Type de données BlackBox."""
    B12_CSB = ids.B12_CSB
    """Type de données B12-CSB."""
    WIBL = ids.WIBL
    """Type de données WIBL."""


DATA_TYPE_MAPPING: {Type[DataParserABC], DataLoggerType} = {
    DataParserOFM: DataLoggerType.OFM,
    DataParserBCDB: DataLoggerType.DCDB,
    DataParserLowrance: DataLoggerType.LOWRANCE,
    DataParserBlackBox: DataLoggerType.BLACKBOX,
    DataParserB12CSB: DataLoggerType.B12_CSB,
    DataParserWIBL: DataLoggerType.WIBL,
}
"""Dictionnaire permettant de faire le lien entre un parser et un type de données."""


T = TypeVar("T", bound=DataParserABC)
"""Type générique permettant de définir un parser."""


@dataclass
class ParserFiles:
    """
    Classe permettant de stocker les fichiers et le parser associés.

    :param parser: Le parser associé aux fichiers.
    :type parser: Type[T]
    :param files: Les fichiers à traiter.
    :type files: list[Path]
    """

    parser: Type[T] = None
    """Le parser associé aux fichiers."""
    files: list[Path] = field(default_factory=list)
    """Les fichiers à traiter."""

    def __setattr__(self, name, value):
        if name == "parser":
            if self.parser is not None:
                if self.parser != value:
                    raise MultipleParsersError(parsers=(self.parser, value))

                return

        super().__setattr__(name, value)

    @property
    def datalogger_type(self) -> DataLoggerType | None:
        """
        Propriété permettant de récupérer le type de données associé.

        :return: Le type de données associé.
        :rtype: DataLoggerType
        """
        if self.parser is None:
            return None

        return DATA_TYPE_MAPPING[self.parser]
