"""
Module qui contient les fonctions de nettoyage des données.

Ce module contient les fonctions qui permettent de nettoyer les données en fonction de critères
"""

from typing import Collection, Optional, Callable, Any, Type

import geopandas as gpd
from loguru import logger
import pandas as pd

from .exception_tranformation import DataCleaningFunctionError
from .transformation_models import DataFilterConfigProtocol
import schema
from schema import model_ids as schema_ids

LOGGER = logger.bind(name="CSB-Pipeline.Transformation.DataCleaning")

DataCleaningFunction = Callable[[gpd.GeoDataFrame, Any], gpd.GeoDataFrame]

MIN_LATITUDE: int | float = -90
MAX_LATITUDE: int | float = 90
MIN_LONGITUDE: int | float = -180
MAX_LONGITUDE: int | float = 180
MIN_DEPTH: int | float = 0
MAX_DEPTH: int | float | None = None


def clean_depth(
    geodataframe: gpd.GeoDataFrame,
    min_depth: int | float = MIN_DEPTH,
    max_depth: Optional[int | float] = MAX_DEPTH,
    **kwargs,
) -> gpd.GeoDataFrame:
    """
    Fonction qui nettoie les données de profondeur.

    :param geodataframe: Le GeoDataFrame.
    :type geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema]
    :param min_depth: La profondeur minimale.
    :type min_depth: int | float
    :param max_depth: La profondeur maximale.
    :type max_depth: int | float | None
    :return: Le GeoDataFrame nettoyé.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerSchema]
    """
    LOGGER.debug(
        f"Nettoyage des données de profondeur {[schema_ids.DEPTH_RAW_METER]}. "
        f"Profondeur minimale : {min_depth}, profondeur maximale : {max_depth}."
    )

    invalid_depths: pd.Series = (
        geodataframe[schema_ids.DEPTH_RAW_METER].isna()
        | (geodataframe[schema_ids.DEPTH_RAW_METER] <= min_depth)
        | (
            geodataframe[schema_ids.DEPTH_RAW_METER] > max_depth
            if max_depth is not None
            else False
        )
    )

    if invalid_depths.any():
        LOGGER.warning(
            f"{invalid_depths.sum()} entrées ont des profondeurs invalides et seront supprimées."
        )

    geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema] = geodataframe[
        ~invalid_depths
    ]

    return geodataframe


def clean_time(geodataframe: gpd.GeoDataFrame, **kwargs) -> gpd.GeoDataFrame:
    """
    Fonction qui nettoie les données de temps.

    :param geodataframe: Le GeoDataFrame à nettoyer.
    :type geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema]
    :return: Le GeoDataFrame nettoyé.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerSchema]
    """
    LOGGER.debug(f"Nettoyage des données de temps {[schema_ids.TIME_UTC]}.")

    current_time: pd.Timestamp = pd.Timestamp.now(tz="UTC")

    invalid_dates: pd.Series = geodataframe[schema_ids.TIME_UTC].isna() | (
        geodataframe[schema_ids.TIME_UTC] > current_time
    )

    if invalid_dates.any():
        LOGGER.warning(
            f"{invalid_dates.sum()} entrées ont des dates invalides et seront supprimées."
        )

    geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema] = geodataframe[
        ~invalid_dates
    ]

    return geodataframe


def clean_latitude(
    geodataframe: gpd.GeoDataFrame,
    min_latitude: int | float = MIN_LATITUDE,
    max_latitude: int | float = MAX_LATITUDE,
    **kwargs,
) -> gpd.GeoDataFrame:
    """
    Fonction qui nettoie les données de latitude.

    :param geodataframe: Le GeoDataFrame à nettoyer.
    :type geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema]
    :param min_latitude: La latitude minimale.
    :type min_latitude: int | float
    :param max_latitude: La latitude maximale.
    :type max_latitude: int | float
    :return: Le GeoDataFrame nettoyé.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerSchema]
    """
    LOGGER.debug(
        f"Nettoyage des données de latitude {[schema_ids.LATITUDE_WGS84]}. "
        f"Latitude minimale : {min_latitude}, latitude maximale : {max_latitude}."
    )

    invalid_latitudes: pd.Series = (
        geodataframe[schema_ids.LATITUDE_WGS84].isna()
        | (geodataframe[schema_ids.LATITUDE_WGS84] < min_latitude)
        | (geodataframe[schema_ids.LATITUDE_WGS84] > max_latitude)
    )
    if invalid_latitudes.any():
        LOGGER.warning(
            f"{invalid_latitudes.sum()} entrées ont des latitudes invalides et seront supprimées."
        )

    geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema] = geodataframe[
        ~invalid_latitudes
    ]

    return geodataframe


def clean_longitude(
    geodataframe: gpd.GeoDataFrame,
    min_longitude: int | float = MIN_LONGITUDE,
    max_longitude: int | float = MAX_LONGITUDE,
    **kwargs,
) -> gpd.GeoDataFrame:
    """
    Fonction qui nettoie les données de longitude.

    :param geodataframe: Le GeoDataFrame à nettoyer.
    :type geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema]
    :param min_longitude: La longitude minimale.
    :type min_longitude: int | float
    :param max_longitude: a longitude maximale.
    :type max_longitude: int | float
    :return: Le GeoDataFrame nettoyé.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerSchema]
    """
    LOGGER.debug(
        f"Nettoyage des données de longitude {[schema_ids.LONGITUDE_WGS84]}. "
        f"Longitude minimale : {min_longitude}, longitude maximale : {max_longitude}."
    )

    invalid_longitudes: pd.Series = (
        geodataframe[schema_ids.LONGITUDE_WGS84].isna()
        | (geodataframe[schema_ids.LONGITUDE_WGS84] < min_longitude)
        | (geodataframe[schema_ids.LONGITUDE_WGS84] > max_longitude)
    )
    if invalid_longitudes.any():
        LOGGER.warning(
            f"{invalid_longitudes.sum()} entrées ont des longitudes invalides et seront suppressées."
        )

    geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema] = geodataframe[
        ~invalid_longitudes
    ]

    return geodataframe


cleaning_function: tuple[Type[DataCleaningFunction], ...] = (
    clean_depth,
    clean_time,
    clean_latitude,
    clean_longitude,
)


def clean_data(
    geodataframe: gpd.GeoDataFrame,
    cleaning_func: Optional[Collection[DataCleaningFunction | str]] = None,
    data_filter: Optional[DataFilterConfigProtocol] = None,
) -> gpd.GeoDataFrame:
    """
    Fonction qui nettoie les données à partir d'une collection de fonctions de nettoyage.

    :param geodataframe: Le GeoDataFrame à nettoyer.
    :type geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema]
    :param cleaning_func: Les fonctions de nettoyage.
    :type cleaning_func: Collection[DataCleaningFunction | str]
    :param data_filter: La configuration de nettoyage.
    :type data_filter: DataFilterConfigProtocol
    :return: Le GeoDataFrame nettoyé.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerSchema]
    :raises DataCleaningFunctionError: Si la fonction de nettoyage n'existe pas.
    """
    LOGGER.debug("Nettoyage des données.")

    if cleaning_func is None:
        cleaning_func = cleaning_function

    for func in cleaning_func:
        if isinstance(func, str):
            globals_ = globals()
            if func not in globals_:
                raise DataCleaningFunctionError(func)

            func = globals_[func]

        geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema] = func(
            geodataframe,
            min_latitude=data_filter.min_latitude if data_filter else MIN_LATITUDE,
            max_latitude=data_filter.max_latitude if data_filter else MAX_LATITUDE,
            min_longitude=data_filter.min_longitude if data_filter else MIN_LONGITUDE,
            max_longitude=data_filter.max_longitude if data_filter else MAX_LONGITUDE,
            min_depth=data_filter.min_depth if data_filter else MIN_DEPTH,
            max_depth=data_filter.max_depth if data_filter else MAX_DEPTH,
        )

    return geodataframe
