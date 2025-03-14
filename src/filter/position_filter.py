"""
Module qui contient les fonctions de nettoyage des données de positionnement.

Ce module contient les fonctions qui permettent de nettoyer les données de positionnement en fonction de critères.
"""

import geopandas as gpd
from loguru import logger
import pandas as pd

import schema
from schema import model_ids as schema_ids

LOGGER = logger.bind(name="CSB-Processing.Filter.Position")


def clean_latitude(
    geodataframe: gpd.GeoDataFrame,
    min_latitude: int | float,
    max_latitude: int | float,
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
    min_longitude: int | float,
    max_longitude: int | float,
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
            f"{invalid_longitudes.sum()} entrées ont des longitudes invalides et seront supprimées."
        )

    geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema] = geodataframe[
        ~invalid_longitudes
    ]

    return geodataframe
