"""
Ce module contient la fonction permettant de récupérer le parser associé à un formtat de fichier.
"""

from pathlib import Path
from typing import Type

import pandas as pd
from loguru import logger

from . import parser_ids as ids
from .parser_exception import ParserIdentifierError
from .parser_abc import DataParserABC
from .parser_dcdb import DataParserBCDB
from .parser_lowrance import DataParserLowrance

LOGGER = logger.bind(name="CSB-Pipeline.Ingestion.Parser.Factory")


DCDB_HEADER: tuple[str, ...] = (
    ids.LONGITUDE_DCDB,
    ids.LATITUDE_DCDB,
    ids.DEPTH_DCDB,
    ids.TIME,
)
LOWRANCE_HEADER: tuple[str, ...] = (
    ids.LONGITUDE_LOWRANCE,
    ids.LATITUDE_LOWRANCE,
    ids.DEPTH_LOWRANCE,
    ids.TIME_LOWRANCE,
)
ACTISENSE_HEADER: tuple[str, ...] = (
    ids.LINE_ACTISENSE,
    ids.TIME_ACTISENSE,
    ids.NAME_ACTISENSE,
    ids.DEPTH_ACTISENSE,
    ids.OFFSET_ACTISENSE,
    ids.POSITION_DATE_ACTISENSE,
    ids.POSITION_TIME_ACTISENSE,
    ids.LATITUDE_ACTISENSE,
    ids.LONGITUDE_ACTISENSE,
    ids.COURSE_OVER_GROUND_ACTISENSE,
    ids.SPEED_OVER_GROUND_ACTISENSE,
    ids.PGN_ACTISENSE,
)
BLACKBOX_HEADER: None = None


FACTORY_PARSER: dict[tuple[str, ...] | None, Type[DataParserABC]] = {
    DCDB_HEADER: DataParserBCDB,
    LOWRANCE_HEADER: DataParserLowrance,
    ACTISENSE_HEADER: "Actisense",
    BLACKBOX_HEADER: "BlackBox",
}


def get_header(file: Path) -> tuple[str, ...] | None:
    """
    Fonction permettant de lire l'entête d'un fichier.

    :param file: Le fichier à lire.
    :type file: Path
    :return: Un tuple contenant les noms des colonnes ou None si l'entête n'est pas trouvé.
    :rtype: tuple[str, ...] | None
    """
    LOGGER.debug(f"Lecture de l'entête du fichier : {file}.")

    try:
        header: pd.DataFrame = pd.read_csv(file, nrows=0)

    except UnicodeDecodeError:
        LOGGER.debug(
            f"Le fichier {file} n'est pas encodé en 'UTF-8'. Tentative en 'latin1'."
        )
        header: pd.DataFrame = pd.read_csv(file, nrows=0, encoding="latin1")

    if any(pd.to_numeric(header.columns, errors="coerce").notna()):
        LOGGER.debug(f"Le fichier {file} n'a pas d'entête.")

        return None

    LOGGER.debug(f"Entête du fichier {file} : {header.columns.tolist()}.")

    return tuple(header.columns.tolist())


def get_parser_factory(file: Path) -> Type[DataParserABC]:
    """
    Fonction permettant de récupérer le parser associé à un fichier.

    :param file: Le fichier à parser.
    :type file: Path
    :return: Le parser associé.
    :rtype: Type[DataParserABC]
    :raises ParserIdentifierError: Si le parser n'est pas trouvé.
    """
    LOGGER.debug(f"Récupération du parser associé au fichier : {file}.")

    header_file: tuple[str, ...] | None = get_header(file)

    if header_file in FACTORY_PARSER:
        return FACTORY_PARSER[header_file]

    for header_signature, parser in FACTORY_PARSER.items():
        if header_signature and all(
            column in header_file for column in header_signature
        ):
            return parser

    raise ParserIdentifierError(file=file)
