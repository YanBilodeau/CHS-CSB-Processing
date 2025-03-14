"""
Module qui contient les fonctions de nettoyage des données de vitesse.

Ce module contient les fonctions qui permettent de nettoyer les données de vitesse en fonction de critères.
"""

import geopandas as gpd
from loguru import logger
import pandas as pd

import schema
from schema import model_ids as schema_ids

LOGGER = logger.bind(name="CSB-Processing.Filter.Speed")


def clean_speed(
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
        f"Nettoyage des données de vitesse {[schema_ids.SPEED_KN]}."
        f"Vitesse minimale : {min_speed}, vitesse maximale : {max_speed}."
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
            f"{invalid_speeds.sum()} entrées ont des vitesses invalides et seront supprimées."
        )

    geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema] = geodataframe[
        ~invalid_speeds
    ]

    return geodataframe
