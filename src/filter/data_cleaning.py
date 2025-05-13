"""
Module qui contient les fonctions de nettoyage des données.

Ce module contient les fonctions qui permettent de nettoyer les données en fonction de critères
"""

from typing import Collection, Optional, Callable, Any, Type

import geopandas as gpd
from loguru import logger

from .datetime_filter import filter_time
from .depth_filter import depth_depth
from .exception_filter import DataCleaningFunctionError
from .filter_models import DataFilterConfigProtocol
from .position_filter import filter_latitude, filter_longitude
from .speed_filter import filter_speed
from .filter_models import FILTER_STATUS_MAPPING, Status
import schema
from schema import model_ids as schema_ids

LOGGER = logger.bind(name="CSB-Processing.Filter.DataCleaning")

DataCleaningFunction = Callable[[gpd.GeoDataFrame, Any], gpd.GeoDataFrame]

MIN_LATITUDE: int | float = -90
MAX_LATITUDE: int | float = 90
MIN_LONGITUDE: int | float = -180
MAX_LONGITUDE: int | float = 180
MIN_DEPTH: int | float = 0
MAX_DEPTH: int | float | None = None
MIN_SPEED: int | float | None = None
MAX_SPEED: int | float | None = None


CLEANING_FUNCTION: tuple[Type[DataCleaningFunction], ...] = (
    depth_depth,
    filter_time,
    filter_latitude,
    filter_longitude,
    filter_speed,
)


def filter_data_by_outlier_tags(
    geodataframe: gpd.GeoDataFrame, tags_to_suppress: list[Status]
) -> gpd.GeoDataFrame:
    """
    Filtre les données du geodataframe en supprimant les lignes contenant certains tags d'outliers.

    :param geodataframe: Le GeoDataFrame à filtrer
    :type geodataframe: gpd.GeoDataFrame
    :param tags_to_suppress: Liste des tags/statuts à supprimer
    :type tags_to_suppress: list[Status]
    :return: Le GeoDataFrame filtré
    :rtype: gpd.GeoDataFrame
    """
    if not tags_to_suppress:
        return geodataframe

    LOGGER.info(f"Suppression des données avec les tags suivants : {tags_to_suppress}.")

    # Compter le nombre de sondes supprimées par tag
    initial_count = len(geodataframe)
    counts_by_tag = {}

    for tag in tags_to_suppress:
        # Identifier les lignes contenant ce tag spécifique
        mask = geodataframe[schema_ids.OUTLIER].apply(
            lambda x: x is not None and tag in x.tags
        )
        counts_by_tag[tag] = mask.sum()

    # Journal des comptages par tag
    for tag, count in counts_by_tag.items():
        if count > 0:
            LOGGER.warning(f"{count:,} sondes supprimées avec le filtre '{tag}'.")

    # Appliquer le filtre
    geodataframe = geodataframe[
        ~geodataframe[schema_ids.OUTLIER].apply(
            lambda x: any(
                tag in (x.tags if x is not None else []) for tag in tags_to_suppress
            )
        )
    ]

    # Compter le nombre de sondes restantes
    final_count = len(geodataframe)
    difference_count = initial_count - final_count
    if difference_count > 0:
        LOGGER.success(f"Nombre de sondes supprimées : {difference_count:,}.")

    return geodataframe


def clean_data(
    geodataframe: gpd.GeoDataFrame,
    cleaning_func: Optional[Collection[DataCleaningFunction | str]] = None,
    data_filter_config: Optional[DataFilterConfigProtocol] = None,
) -> gpd.GeoDataFrame:
    """
    Fonction qui nettoie les données à partir d'une collection de fonctions de nettoyage.

    :param geodataframe: Le GeoDataFrame à nettoyer.
    :type geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema]
    :param cleaning_func: Les fonctions de nettoyage.
    :type cleaning_func: Collection[DataCleaningFunction | str]
    :param data_filter_config: La configuration de nettoyage.
    :type data_filter_config: DataFilterConfigProtocol
    :return: Le GeoDataFrame nettoyé.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerSchema]
    :raises DataCleaningFunctionError: Si la fonction de nettoyage n'existe pas.
    """
    LOGGER.debug("Nettoyage des données.")

    if cleaning_func is None:
        cleaning_func = CLEANING_FUNCTION

    for func in cleaning_func:
        if isinstance(func, str):
            globals_ = globals()
            if func not in globals_:
                raise DataCleaningFunctionError(func)

            func = globals_[func]

        geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema] = func(
            geodataframe,
            min_latitude=(
                data_filter_config.min_latitude if data_filter_config else MIN_LATITUDE
            ),
            max_latitude=(
                data_filter_config.max_latitude if data_filter_config else MAX_LATITUDE
            ),
            min_longitude=(
                data_filter_config.min_longitude
                if data_filter_config
                else MIN_LONGITUDE
            ),
            max_longitude=(
                data_filter_config.max_longitude
                if data_filter_config
                else MAX_LONGITUDE
            ),
            min_depth=data_filter_config.min_depth if data_filter_config else MIN_DEPTH,
            max_depth=data_filter_config.max_depth if data_filter_config else MAX_DEPTH,
            min_speed=data_filter_config.min_speed if data_filter_config else MIN_SPEED,
            max_speed=data_filter_config.max_speed if data_filter_config else MAX_SPEED,
        )

    tags_to_suppress: list[Status] = [
        FILTER_STATUS_MAPPING[tag] for tag in data_filter_config.filter_to_apply  # type: ignore
    ]

    geodataframe = filter_data_by_outlier_tags(geodataframe, tags_to_suppress)

    return geodataframe
