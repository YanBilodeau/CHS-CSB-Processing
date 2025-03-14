"""
Module qui contient les fonctions de nettoyage des données.

Ce module contient les fonctions qui permettent de nettoyer les données en fonction de critères
"""

from typing import Collection, Optional, Callable, Any, Type

import geopandas as gpd
from loguru import logger

from .datetime_filter import clean_time
from .depth_filter import clean_depth
from .exception_filter import DataCleaningFunctionError
from .filter_models import DataFilterConfigProtocol
from .position_filter import clean_latitude, clean_longitude
from .speed_filter import clean_speed
import schema

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
    clean_depth,
    clean_time,
    clean_latitude,
    clean_longitude,
    clean_speed,
)


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

    return geodataframe
