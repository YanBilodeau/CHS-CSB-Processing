"""
Module qui contient les fonctions de nettoyage des données de positionnement.

Ce module contient les fonctions qui permettent de nettoyer les données de positionnement en fonction de critères.
"""

import geopandas as gpd
import i18n
from loguru import logger
import pandas as pd

import schema
from schema import model_ids as schema_ids
from .filter_models import Status

LOGGER = logger.bind(name="CSB-Processing.Filter.Position")


def filter_latitude(
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
        i18n.t(
            "filter.position_filter.cleaning_latitude",
            column=[schema_ids.LATITUDE_WGS84],
            min_latitude=min_latitude,
            max_latitude=max_latitude,
        )
    )

    invalid_latitudes: pd.Series = (
        geodataframe[schema_ids.LATITUDE_WGS84].isna()
        | (geodataframe[schema_ids.LATITUDE_WGS84] < min_latitude)
        | (geodataframe[schema_ids.LATITUDE_WGS84] > max_latitude)
    )
    if invalid_latitudes.any():
        LOGGER.warning(
            i18n.t(
                "filter.position_filter.invalid_latitudes",
                count=f"{invalid_latitudes.sum():,}",
            )
        )

        geodataframe.loc[invalid_latitudes, schema_ids.OUTLIER] = geodataframe.loc[
            invalid_latitudes, schema_ids.OUTLIER
        ].apply(lambda x: x.tags.append(Status.REJECTED_BY_LATITUDE_FILTER) or x)

    return geodataframe


def filter_longitude(
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
        i18n.t(
            "filter.position_filter.cleaning_longitude",
            column=[schema_ids.LONGITUDE_WGS84],
            min_longitude=min_longitude,
            max_longitude=max_longitude,
        )
    )

    invalid_longitudes: pd.Series = (
        geodataframe[schema_ids.LONGITUDE_WGS84].isna()
        | (geodataframe[schema_ids.LONGITUDE_WGS84] < min_longitude)
        | (geodataframe[schema_ids.LONGITUDE_WGS84] > max_longitude)
    )
    if invalid_longitudes.any():
        LOGGER.warning(
            i18n.t(
                "filter.position_filter.invalid_longitudes",
                count=f"{invalid_longitudes.sum()}",
            )
        )

        geodataframe.loc[invalid_longitudes, schema_ids.OUTLIER] = geodataframe.loc[
            invalid_longitudes, schema_ids.OUTLIER
        ].apply(lambda x: x.tags.append(Status.REJECTED_BY_LONGITUDE_FILTER) or x)

    return geodataframe
