"""
Calculateur de distances géographiques entre points consécutifs.

Ce module fournit les fonctions de calcul de distance en utilisant
une projection UTM automatique pour une précision métrique.
"""

import geopandas as gpd
import pandas as pd

from .crs_operations import project_to_utm
from .models import DistanceStats

NM_PER_METER: float = 0.000539957
"""Facteur de conversion mètres → milles nautiques."""

KM_PER_METER: float = 0.001
"""Facteur de conversion mètres → kilomètres."""


def add_distance_column(
    gdf: gpd.GeoDataFrame, col: str = "distance_m"
) -> gpd.GeoDataFrame:
    """
    Ajoute une colonne de distance en mètres entre points consécutifs.

    La zone UTM est déterminée automatiquement. Le premier point reçoit NaN.

    :param gdf: GeoDataFrame en WGS84 avec DatetimeIndex trié.
    :type gdf: gpd.GeoDataFrame
    :param col: Nom de la colonne à créer.
    :type col: str
    :return: GeoDataFrame original (WGS84) enrichi de la colonne distance.
    :rtype: gpd.GeoDataFrame
    """
    gdf_utm, _ = project_to_utm(gdf)
    distances = gdf_utm.geometry.distance(gdf_utm.geometry.shift(1))

    gdf = gdf.copy()
    gdf[col] = distances.values

    return gdf


def compute_total_distance(
    gdf: gpd.GeoDataFrame, col: str = "distance_m"
) -> DistanceStats:
    """
    Calcule la distance totale parcourue entre tous les points.

    :param gdf: GeoDataFrame avec la colonne de distance (mètres).
    :type gdf: gpd.GeoDataFrame
    :param col: Nom de la colonne distance.
    :type col: str
    :return: Statistiques de distance totale.
    :rtype: DistanceStats
    :raises KeyError: Si la colonne est absente.
    """
    if col not in gdf.columns:
        raise KeyError(
            f"Colonne '{col}' introuvable. " f"Appelez d'abord add_distance_column()."
        )

    total_m = gdf[col].sum(skipna=True)

    return DistanceStats(
        meters=round(total_m, 3),
        kilometers=round(total_m * KM_PER_METER, 3),
        nautical_miles=round(total_m * NM_PER_METER, 3),
    )


def compute_daily_distances(
    gdf: gpd.GeoDataFrame, col: str = "distance_m"
) -> dict[str, DistanceStats]:
    """
    Calcule la distance sondée par journée UTC.

    Les NaN (frontières de journée, points filtrés) sont ignorés (skipna=True).

    :param gdf: GeoDataFrame avec DatetimeIndex UTC et colonne distance.
    :type gdf: gpd.GeoDataFrame
    :param col: Nom de la colonne distance (mètres).
    :type col: str
    :return: Dictionnaire {date_str: DistanceStats}.
    :rtype: dict[str, DistanceStats]
    :raises KeyError: Si la colonne est absente.
    """
    if col not in gdf.columns:
        raise KeyError(
            f"Colonne '{col}' introuvable. " f"Appelez d'abord add_distance_column()."
        )

    daily_totals: pd.Series = gdf.groupby(pd.DatetimeIndex(gdf.index).date)[col].sum()

    result: dict[str, DistanceStats] = {}
    for date, total_m in daily_totals.items():
        date_str = date.isoformat()
        result[date_str] = DistanceStats(
            meters=round(total_m, 3),
            kilometers=round(total_m * KM_PER_METER, 3),
            nautical_miles=round(total_m * NM_PER_METER, 3),
        )

    return result
