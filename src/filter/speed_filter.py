"""
Module qui contient les fonctions de nettoyage des données de vitesse.

Ce module contient les fonctions qui permettent de nettoyer les données de vitesse en fonction de critères.
"""

import geopandas as gpd
import i18n
from loguru import logger
import pandas as pd

import schema
from schema import model_ids as schema_ids
from .filter_models import Status

LOGGER = logger.bind(name="CSB-Processing.Filter.Speed")


def filter_speed(
    geodataframe: gpd.GeoDataFrame,
    min_speed: int | float | None,
    max_speed: int | float | None,
    **kwargs,
) -> gpd.GeoDataFrame:
    """
    Fonction qui nettoie les données de vitesse.

    :param geodataframe: Le GeoDataFrame à nettoyer.
    :type geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema]
    :param min_speed: La vitesse minimale.
    :type min_speed: int | float | None
    :param max_speed: La vitesse maximale.
    :type max_speed: int | float | None
    :return: Le GeoDataFrame nettoyé.
    """
    LOGGER.debug(
        i18n.t(
            "filter.speed_filter.cleaning_speed",
            column=[schema_ids.SPEED_KN],
            min_speed=min_speed,
            max_speed=max_speed,
        )
    )

    invalid_speeds: pd.Series = (~geodataframe[schema_ids.SPEED_KN].isna()) & (
        (
            geodataframe[schema_ids.SPEED_KN] < min_speed
            if min_speed is not None
            else False
        )
        | (
            geodataframe[schema_ids.SPEED_KN] > max_speed
            if max_speed is not None
            else False
        )
    )

    if invalid_speeds.any():
        LOGGER.warning(
            i18n.t(
                "filter.speed_filter.invalid_speeds", count=f"{invalid_speeds.sum():,}"
            )
        )

        geodataframe.loc[invalid_speeds, schema_ids.OUTLIER] = geodataframe.loc[
            invalid_speeds, schema_ids.OUTLIER
        ].apply(lambda x: x.tags.append(Status.REJECTED_BY_SPEED_FILTER) or x)

    return geodataframe
