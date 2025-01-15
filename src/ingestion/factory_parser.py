"""
Module permettant de récupérer le parser associé à un fichier.

Ce module contient les fonctions permettant de récupérer le parser associé à un fichier.
"""

from pathlib import Path
from typing import Type, Collection

import pandas as pd
from loguru import logger

from . import parser_ids as ids
from .parser_abc import DataParserABC
from .parser_dcdb import DataParserBCDB
from .parser_lowrance import DataParserLowrance
from .parser_ofm import DataParserOFM
from .parser_exception import ParserIdentifierError
from .parser_models import ParserFiles

LOGGER = logger.bind(name="CSB-Processing.Ingestion.Parser.Factory")

Header = tuple[str, ...]
"""Alias pour un tuple de str représentant une entête."""

DCDB_HEADER: Header = (
    ids.LONGITUDE_DCDB,
    ids.LATITUDE_DCDB,
    ids.DEPTH_DCDB,
    ids.TIME_DCDB,
)
"""Entête des fichiers DCDB."""

OFM_HEADER: Header = (
    ids.LONGITUDE_OFM,
    ids.LATITUDE_OFM,
    ids.DEPTH_OFM,
    ids.TIME_OFM,
)
"""Entête des fichiers OFM."""

LOWRANCE_HEADER: Header = (
    ids.LONGITUDE_LOWRANCE,
    ids.LATITUDE_LOWRANCE,
    ids.DEPTH_LOWRANCE,
    ids.TIME_LOWRANCE,
    ids.SURVEY_TYPE_LOWRANCE,
)
"""Entête des fichiers Lowrance."""

ACTISENSE_HEADER: Header = (
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
"""Entête des fichiers Actisense."""

BLACKBOX_HEADER: None = None
"""Entête des fichiers BlackBox."""


FACTORY_PARSER: dict[tuple[Header | None, str], Type[DataParserABC]] = {
    (DCDB_HEADER, ids.EXTENSION_CSV): DataParserBCDB,
    (OFM_HEADER, ids.EXTENSION_XYZ): DataParserOFM,
    (LOWRANCE_HEADER, ids.EXTENSION_CSV): DataParserLowrance,
    (ACTISENSE_HEADER, ids.EXTENSION_CSV): "Actisense",
    (BLACKBOX_HEADER, ids.EXTENSION_TXT): "BlackBox",
}
"""Dictionnaire associant les entêtes et les extensions aux parsers."""


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


def get_extension(file: Path) -> str:
    """
    Fonction permettant de récupérer l'extension d'un fichier.

    :param file: Le fichier a à analyser.
    :type file: Path
    :return: L'extension du fichier.
    :rtype: str
    """
    LOGGER.debug(f"Récupération de l'extension du fichier : {file}.")

    extension: str = file.suffix

    LOGGER.debug(f"Extension du fichier {file} : {extension}.")

    return extension


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
    extension: str = get_extension(file)
    key: tuple[Header | None, str] = (header_file, extension)

    if key in FACTORY_PARSER:
        return FACTORY_PARSER[key]

    for (format_header, format_extension), parser in FACTORY_PARSER.items():
        if (
            format_header
            and all(column in header_file for column in format_header)
            and format_extension == extension
        ):
            return parser

    raise ParserIdentifierError(file=file)


def get_files_parser(files: Collection[Path,]) -> ParserFiles:
    """
    Fonction permettant de trouver les parsers associés aux fichiers.

    :param files: Les fichiers à traiter.
    :type files: Collection[Path]
    :return: Un objet ParserFiles contenant le parser associés aux fichiers.
    :rtype: ParserFiles
    :raises factory_parser.ParserIdentifierError: Si une erreur survient lors de l'identification du parser.
    :raises factory_parser.MultipleParsersError: Si plusieurs parsers sont identifiés.
    """
    parser_files: ParserFiles = ParserFiles()

    for file in files:
        LOGGER.debug(f"Traitement du fichier : {file}.")

        try:
            parser: Type[DataParserABC] = get_parser_factory(file)
            LOGGER.debug(
                f"Parser identifié pour le fichier {file} : {parser.__name__}."
            )

        except ParserIdentifierError as error:
            LOGGER.error(error)
            raise error

        parser_files.parser = parser
        parser_files.files.append(file)

    return parser_files
