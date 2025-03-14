"""
Module qui contient les fonctions de nettoyage des données.

Ce module contient les fonctions qui permettent de nettoyer les données de profondeur.
"""

import geopandas as gpd
from loguru import logger
import pandas as pd

import schema
from schema import model_ids as schema_ids

LOGGER = logger.bind(name="CSB-Processing.Filter.Depth")


def clean_depth(
    geodataframe: gpd.GeoDataFrame,
    min_depth: int | float,
    max_depth: int | float | None,
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
