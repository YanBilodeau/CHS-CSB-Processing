"""
Module de chargement et de nettoyage des données brutes CSB.

Ce module encapsule l'étape d'ingestion complète : identification du parseur,
création du :class:`~processing_context.ProcessingContext`, parsing et nettoyage.
"""

from __future__ import annotations

from collections.abc import Collection
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import geopandas as gpd
import i18n
from loguru import logger

from . import factory_parser
import filter.data_cleaning as cleaner
import schema

if TYPE_CHECKING:
    from processing_context import ProcessingContext


LOGGER = logger.bind(name="CSB-Processing.Ingestion.DataLoader")


def load_and_clean_data(
    files: Collection[Path],
    data_filter_config,
    already_at_chart_datum: bool = False,
) -> Optional[tuple[gpd.GeoDataFrame, "ProcessingContext"]]:
    """
    Charge, parse et nettoie les données brutes CSB.

    Crée le :class:`~processing_context.ProcessingContext` d'après le type de capteur
    identifié par le parseur, puis retourne les données nettoyées avec leur contexte.

    :param files: Fichiers bruts à traiter.
    :type files: Collection[Path]
    :param data_filter_config: Configuration des filtres (``processing_config.filter``).
    :param already_at_chart_datum: ``True`` si les données sont déjà réduites au zéro des cartes.
    :type already_at_chart_datum: bool
    :return: ``(data, ctx)`` ou ``None`` si aucune donnée valide.
    :rtype: Optional[tuple[gpd.GeoDataFrame, ProcessingContext]]
    """
    from processing_context import ProcessingContext  # import local — évite le cycle

    parser_files: factory_parser.ParserFiles = factory_parser.get_files_parser(
        files=files
    )
    LOGGER.debug(parser_files)

    if not parser_files.files:
        LOGGER.warning(i18n.t("ingestion.data_loader.no_valid_files"))
        return None

    ctx = ProcessingContext(
        datalogger_type=parser_files.datalogger_type,
        already_at_chart_datum=already_at_chart_datum,
    )

    data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema] = (
        parser_files.parser.from_files(files=parser_files.files)
    )
    if data.empty:
        LOGGER.warning(i18n.t("ingestion.data_loader.no_valid_data"))
        return None

    LOGGER.info(i18n.t("ingestion.data_loader.cleaning_data"))
    data = cleaner.clean_data(data, data_filter_config=data_filter_config)
    if data.empty:
        LOGGER.warning(i18n.t("ingestion.data_loader.no_valid_soundings"))
        return None

    LOGGER.success(
        i18n.t("ingestion.data_loader.soundings_retrieved", count=f"{len(data):,}")
    )

    return data, ctx
