"""
Calculateur de durées de sondage.

Ce module fournit les fonctions de calcul de temps total et par jour,
basées sur la colonne deltatime (Timedelta).
"""

import geopandas as gpd
import pandas as pd

from .models import DistanceStats, TimeStats

SECONDS_PER_MINUTE: float = 60.0
"""Facteur de conversion secondes → minutes."""

SECONDS_PER_HOUR: float = 3600.0
"""Facteur de conversion secondes → heures."""

SECONDS_PER_DAY: float = 86400.0
"""Facteur de conversion secondes → jours."""


def compute_total_time(gdf: gpd.GeoDataFrame, col: str = "deltatime") -> TimeStats:
    """
    Calcule le temps total de sondage à partir de la colonne deltatime.

    Les NaT (premier point, frontières de journée) sont ignorés (skipna=True).

    :param gdf: GeoDataFrame avec la colonne deltatime (Timedelta).
    :type gdf: gpd.GeoDataFrame
    :param col: Nom de la colonne deltatime.
    :type col: str
    :return: Statistiques de temps total.
    :rtype: TimeStats
    :raises KeyError: Si la colonne est absente.
    """
    if col not in gdf.columns:
        raise KeyError(
            f"Colonne '{col}' introuvable. " f"Appelez d'abord add_deltatime_column()."
        )

    total_timedelta: pd.Timedelta = gdf[col].sum(skipna=True)
    total_seconds = total_timedelta.total_seconds()

    return TimeStats(
        total_seconds=round(total_seconds, 3),
        total_minutes=round(total_seconds / SECONDS_PER_MINUTE, 3),
        total_hours=round(total_seconds / SECONDS_PER_HOUR, 3),
        total_days=round(total_seconds / SECONDS_PER_DAY, 3),
    )


def compute_daily_times(
    gdf: gpd.GeoDataFrame, col: str = "deltatime"
) -> dict[str, TimeStats]:
    """
    Calcule le temps de sondage par journée UTC.

    Les NaT (premier point de journée, points filtrés) sont ignorés (skipna=True).

    :param gdf: GeoDataFrame avec DatetimeIndex UTC et colonne deltatime.
    :type gdf: gpd.GeoDataFrame
    :param col: Nom de la colonne deltatime (Timedelta).
    :type col: str
    :return: Dictionnaire {date_str: TimeStats}.
    :rtype: dict[str, TimeStats]
    :raises KeyError: Si la colonne est absente.
    """
    if col not in gdf.columns:
        raise KeyError(
            f"Colonne '{col}' introuvable. " f"Appelez d'abord add_deltatime_column()."
        )

    daily_totals: pd.Series = gdf.groupby(pd.DatetimeIndex(gdf.index).date)[col].sum()

    result: dict[str, TimeStats] = {}
    for date, total_timedelta in daily_totals.items():
        total_seconds = total_timedelta.total_seconds()
        date_str = date.isoformat()

        result[date_str] = TimeStats(
            total_seconds=round(total_seconds, 3),
            total_minutes=round(total_seconds / SECONDS_PER_MINUTE, 3),
            total_hours=round(total_seconds / SECONDS_PER_HOUR, 3),
            total_days=round(total_seconds / SECONDS_PER_DAY, 3),
        )

    return result


def compute_surveying_speed(distance: DistanceStats, time: TimeStats) -> float:
    """
    Calcule la vitesse moyenne de sondage en nœuds.

    :param distance: Statistiques de distance parcourue.
    :type distance: DistanceStats
    :param time: Statistiques de temps de sondage.
    :type time: TimeStats
    :return: Vitesse moyenne en nœuds (NM/h).
    :rtype: float
    """
    if time.total_hours == 0:
        return 0.0

    speed_knots = distance.nautical_miles / time.total_hours
    return round(speed_knots, 3)
