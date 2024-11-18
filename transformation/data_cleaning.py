from typing import Collection, Optional, Callable

import geopandas as gpd
from loguru import logger

from schema.model import DataLoggerSchema

LOGGER = logger.bind(name="CSB-Pipeline.Transformation.DataCleaning")

CleaningFunction = Callable[[gpd.GeoDataFrame], gpd.GeoDataFrame]


def clean_depth(geodataframe: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Fonction qui nettoie les données de profondeur.

    :param geodataframe: (gpd.GeoDataFrame[DataLoggerSchema]) Le GeoDataFrame.
    :return: (gpd.GeoDataFrame[DataLoggerSchema]) Le GeoDataFrame nettoyé.
    """
    LOGGER.debug("Nettoyage des données de profondeur.")

    geodataframe: gpd.GeoDataFrame[DataLoggerSchema] = geodataframe[
        geodataframe["Depth_meter"].notna() & (geodataframe["Depth_meter"] > 0)
    ]

    return geodataframe


def clean_time(geodataframe: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Fonction qui nettoie les données de temps.

    :param geodataframe: (gpd.GeoDataFrame[DataLoggerSchema]) Le GeoDataFrame.
    :return: (gpd.GeoDataFrame[DataLoggerSchema]) Le GeoDataFrame nettoyé.
    """
    LOGGER.debug("Nettoyage des données de temps.")

    geodataframe: gpd.GeoDataFrame[DataLoggerSchema] = geodataframe[
        geodataframe["Time_UTC"].notna()
    ]

    return geodataframe


def clean_latitude(geodataframe: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Fonction qui nettoie les données de latitude.

    :param geodataframe: (gpd.GeoDataFrame[DataLoggerSchema]) Le GeoDataFrame.
    :return: (gpd.GeoDataFrame[DataLoggerSchema]) Le GeoDataFrame nettoyé.
    """
    LOGGER.debug("Nettoyage des données de latitude.")

    geodataframe: gpd.GeoDataFrame[DataLoggerSchema] = geodataframe[
        geodataframe["Latitude_WGS84"].notna()
        & (geodataframe["Latitude_WGS84"] >= -90)
        & (geodataframe["Latitude_WGS84"] <= 90)
    ]

    return geodataframe


def clean_longitude(geodataframe: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Fonction qui nettoie les données de longitude.

    :param geodataframe: (gpd.GeoDataFrame[DataLoggerSchema]) Le GeoDataFrame.
    :return: (gpd.GeoDataFrame[DataLoggerSchema]) Le GeoDataFrame nettoyé.
    """
    LOGGER.debug("Nettoyage des données de longitude.")

    geodataframe: gpd.GeoDataFrame[DataLoggerSchema] = geodataframe[
        geodataframe["Longitude_WGS84"].notna()
        & (geodataframe["Longitude_WGS84"] >= -180)
        & (geodataframe["Longitude_WGS84"] <= 180)
    ]

    return geodataframe


cleaning_function: tuple[CleaningFunction, ...] = (
    clean_depth,
    clean_time,
    clean_latitude,
    clean_longitude,
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
    LOGGER.info("Nettoyage des données.")

    if cleaning_func is None:
        cleaning_func = cleaning_function

    for func in cleaning_func:
        if isinstance(func, str):
            func = globals()[func]

        geodataframe = func(geodataframe)

    return geodataframe
