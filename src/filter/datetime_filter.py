"""
Module qui contient les fonctions de nettoyage des données de temps.

Ce module contient les fonctions qui permettent de nettoyer les données de temps.
"""

import geopandas as gpd
from loguru import logger
import pandas as pd

import schema
from schema import model_ids as schema_ids
from .status import Status

LOGGER = logger.bind(name="CSB-Processing.Filter.Datetime")


def filter_time(geodataframe: gpd.GeoDataFrame, **kwargs) -> gpd.GeoDataFrame:
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
        LOGGER.warning(f"{invalid_dates.sum():,} entrées ont des dates invalides.")

        geodataframe.loc[invalid_dates, schema_ids.OUTLIER] = geodataframe.loc[
            invalid_dates, schema_ids.OUTLIER
        ].apply(lambda x: x + [Status.REJECTED_BY_TIME_FILTER])

    # geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema] = geodataframe[
    #     ~invalid_dates
    # ]

    return geodataframe
