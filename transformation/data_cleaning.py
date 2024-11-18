from functools import partial
from typing import Collection, Optional, Callable, Any, Type

import geopandas as gpd
from loguru import logger

from schema import (
    DataLoggerSchema,
    DEPTH_METER,
    TIME_UTC,
    LATITUDE_WGS84,
    LONGITUDE_WGS84,
)

LOGGER = logger.bind(name="CSB-Pipeline.Transformation.DataCleaning")

CleaningFunction = Callable[[gpd.GeoDataFrame, Any], gpd.GeoDataFrame]

MIN_LATITUDE: int = -90
MAX_LATITUDE: int = 90
MIN_LONGITUDE: int = -180
MAX_LONGITUDE: int = 180


def clean_depth(geodataframe: gpd.GeoDataFrame, **kwargs) -> gpd.GeoDataFrame:
    """
    Fonction qui nettoie les données de profondeur.

    :param geodataframe: (gpd.GeoDataFrame[DataLoggerSchema]) Le GeoDataFrame.
    :return: (gpd.GeoDataFrame[DataLoggerSchema]) Le GeoDataFrame nettoyé.
    """
    LOGGER.debug(f"Nettoyage des données de profondeur {[DEPTH_METER]}.")

    geodataframe: gpd.GeoDataFrame[DataLoggerSchema] = geodataframe[
        geodataframe[DEPTH_METER].notna() & (geodataframe[DEPTH_METER] > 0)
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
    min_latitude: int = MIN_LATITUDE,
    max_latitude: int = MAX_LATITUDE,
    **kwargs,
) -> gpd.GeoDataFrame:
    """
    Fonction qui nettoie les données de latitude.

    :param geodataframe: (gpd.GeoDataFrame[DataLoggerSchema]) Le GeoDataFrame.
    :param min_latitude: (int) La latitude minimale.
    :param max_latitude: (int) La latitude maximale.
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
    min_longitude: int = MIN_LONGITUDE,
    max_longitude: int = MAX_LONGITUDE,
    **kwargs,
) -> gpd.GeoDataFrame:
    """
    Fonction qui nettoie les données de longitude.

    :param geodataframe: (gpd.GeoDataFrame[DataLoggerSchema]) Le GeoDataFrame.
    :param min_longitude: (int) La longitude minimale.
    :param max_longitude: (int) La longitude maximale.
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


cleaning_function: tuple[Type[CleaningFunction], ...] = (
    clean_depth,
    clean_time,
    partial(clean_latitude, min_latitude=MIN_LATITUDE, max_latitude=MAX_LATITUDE),
    partial(clean_longitude, min_longitude=MIN_LONGITUDE, max_longitude=MAX_LONGITUDE),
)


def clean_data(
    geodataframe: gpd.GeoDataFrame,
    cleaning_func: Optional[Collection[CleaningFunction | str]] = None,
) -> gpd.GeoDataFrame:
    """
    Fonction qui nettoie les données à partir d'une collection de fonctions de nettoyage.

    :param geodataframe: (gpd.GeoDataFrame[DataLoggerSchema]) Le GeoDataFrame.
    :param cleaning_func: (Collection[CleanerFunctionProtocol | str]) Les fonctions de nettoyage.
    :return: (gpd.GeoDataFrame[DataLoggerSchema]) Le GeoDataFrame nettoyé.
    """
    LOGGER.debug("Nettoyage des données.")

    if cleaning_func is None:
        cleaning_func = cleaning_function

    for func in cleaning_func:
        if isinstance(func, str):
            func = globals()[func]

        geodataframe: gpd.GeoDataFrame[DataLoggerSchema] = func(geodataframe)

    return geodataframe
