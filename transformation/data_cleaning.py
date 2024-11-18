from typing import Collection, Optional, Callable, Any, Type, Protocol

import geopandas as gpd
from loguru import logger

from .exception_tranformation import DataCleaningFunctionError
from schema import (
    DataLoggerSchema,
    DEPTH_METER,
    TIME_UTC,
    LATITUDE_WGS84,
    LONGITUDE_WGS84,
)

LOGGER = logger.bind(name="CSB-Pipeline.Transformation.DataCleaning")

DataCleaningFunction = Callable[[gpd.GeoDataFrame, Any], gpd.GeoDataFrame]

MIN_LATITUDE: int | float = -90
MAX_LATITUDE: int | float = 90
MIN_LONGITUDE: int | float = -180
MAX_LONGITUDE: int | float = 180
MIN_DEPTH: int | float = 0
MAX_DEPTH: int | float | None = None


class DataFilterConfigProtocol(Protocol):
    min_latitude: int | float
    max_latitude: int | float
    min_longitude: int | float
    max_longitude: int | float
    min_depth: int | float
    max_depth: Optional[int | float]


def clean_depth(
    geodataframe: gpd.GeoDataFrame,
    min_depth: int | float = MIN_DEPTH,
    max_depth: Optional[int | float] = MAX_DEPTH,
    **kwargs,
) -> gpd.GeoDataFrame:
    """
    Fonction qui nettoie les données de profondeur.

    :param geodataframe: (gpd.GeoDataFrame[DataLoggerSchema]) Le GeoDataFrame.
    :param min_depth: (int | float) La profondeur minimale.
    :param max_depth: (Optional[int | float]) La profondeur maximale.
    :return: (gpd.GeoDataFrame[DataLoggerSchema]) Le GeoDataFrame nettoyé.
    """
    LOGGER.debug(
        f"Nettoyage des données de profondeur {[DEPTH_METER]}. "
        f"Profondeur minimale : {min_depth}, profondeur maximale : {max_depth}."
    )

    geodataframe: gpd.GeoDataFrame[DataLoggerSchema] = geodataframe[
        geodataframe[DEPTH_METER].notna() & (geodataframe[DEPTH_METER] > min_depth)
    ]

    if max_depth is not None:
        geodataframe: gpd.GeoDataFrame[DataLoggerSchema] = geodataframe[
            geodataframe[DEPTH_METER] <= max_depth
        ]

    return geodataframe


def clean_time(geodataframe: gpd.GeoDataFrame, **kwargs) -> gpd.GeoDataFrame:
    """
    Fonction qui nettoie les données de temps.

    :param geodataframe: (gpd.GeoDataFrame[DataLoggerSchema]) Le GeoDataFrame.
    :return: (gpd.GeoDataFrame[DataLoggerSchema]) Le GeoDataFrame nettoyé.
    """
    LOGGER.debug(f"Nettoyage des données de temps {[TIME_UTC]}.")

    geodataframe: gpd.GeoDataFrame[DataLoggerSchema] = geodataframe[
        geodataframe[TIME_UTC].notna()
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

    :param geodataframe: (gpd.GeoDataFrame[DataLoggerSchema]) Le GeoDataFrame.
    :param min_latitude: (int | float) La latitude minimale.
    :param max_latitude: (int | float) La latitude maximale.
    :return: (gpd.GeoDataFrame[DataLoggerSchema]) Le GeoDataFrame nettoyé.
    """
    LOGGER.debug(
        f"Nettoyage des données de latitude {[LATITUDE_WGS84]}. "
        f"Latitude minimale : {min_latitude}, latitude maximale : {max_latitude}."
    )

    geodataframe: gpd.GeoDataFrame[DataLoggerSchema] = geodataframe[
        geodataframe[LATITUDE_WGS84].notna()
        & (geodataframe[LATITUDE_WGS84] >= min_latitude)
        & (geodataframe[LATITUDE_WGS84] <= max_latitude)
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

    :param geodataframe: (gpd.GeoDataFrame[DataLoggerSchema]) Le GeoDataFrame.
    :param min_longitude: (int | float) La longitude minimale.
    :param max_longitude: (int | float) La longitude maximale.
    :return: (gpd.GeoDataFrame[DataLoggerSchema]) Le GeoDataFrame nettoyé.
    """
    LOGGER.debug(
        f"Nettoyage des données de longitude {[LONGITUDE_WGS84]}. "
        f"Longitude minimale : {min_longitude}, longitude maximale : {max_longitude}."
    )

    geodataframe: gpd.GeoDataFrame[DataLoggerSchema] = geodataframe[
        geodataframe[LONGITUDE_WGS84].notna()
        & (geodataframe[LONGITUDE_WGS84] >= min_longitude)
        & (geodataframe[LONGITUDE_WGS84] <= max_longitude)
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

    :param geodataframe: (gpd.GeoDataFrame[DataLoggerSchema]) Le GeoDataFrame.
    :param cleaning_func: (Collection[CleanerFunctionProtocol | str]) Les fonctions de nettoyage.
    :param data_filter: (Optional[DataFilterConfigProtocol]) La configuration de nettoyage.
    :return: (gpd.GeoDataFrame[DataLoggerSchema]) Le GeoDataFrame nettoyé.
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

        geodataframe: gpd.GeoDataFrame[DataLoggerSchema] = func(
            geodataframe,
            min_latitude=data_filter.min_latitude if data_filter else MIN_LATITUDE,
            max_latitude=data_filter.max_latitude if data_filter else MAX_LATITUDE,
            min_longitude=data_filter.min_longitude if data_filter else MIN_LONGITUDE,
            max_longitude=data_filter.max_longitude if data_filter else MAX_LONGITUDE,
            min_depth=data_filter.min_depth if data_filter else MIN_DEPTH,
            max_depth=data_filter.max_depth if data_filter else MAX_DEPTH,
        )

    return geodataframe
