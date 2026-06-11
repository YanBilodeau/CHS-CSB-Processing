"""
Agrégation des statistiques de levé bathymétrique.

Ce module assemble les statistiques journalières et totales
en combinant distance, temps et nombre de points.
"""

import geopandas as gpd
import pandas as pd

from .distance_calculator import compute_daily_distances, compute_total_distance
from .models import DailyStats, SurveyStatistics
from .time_calculator import compute_daily_times, compute_total_time


def aggregate_daily_statistics(
    gdf: gpd.GeoDataFrame,
    distance_col: str = "distance_m",
    deltatime_col: str = "deltatime",
) -> list[DailyStats]:
    """
    Agrège les statistiques par jour (distance + temps + count).

    :param gdf: GeoDataFrame avec DatetimeIndex UTC, distance et deltatime.
    :type gdf: gpd.GeoDataFrame
    :param distance_col: Nom de la colonne distance (mètres).
    :type distance_col: str
    :param deltatime_col: Nom de la colonne deltatime.
    :type deltatime_col: str
    :return: Liste de DailyStats triée par date.
    :rtype: list[DailyStats]
    """
    daily_distances = compute_daily_distances(gdf, col=distance_col)
    daily_times = compute_daily_times(gdf, col=deltatime_col)

    # Compter les points par jour
    daily_counts: pd.Series = gdf.groupby(pd.DatetimeIndex(gdf.index).date).size()

    # Combiner toutes les stats par date
    all_dates = sorted(set(daily_distances.keys()) | set(daily_times.keys()))

    daily_stats_list: list[DailyStats] = []
    for date_str in all_dates:
        count = daily_counts.get(pd.to_datetime(date_str).date(), 0)

        daily_stats_list.append(
            DailyStats(
                date=date_str,
                distance=daily_distances[date_str],
                time=daily_times[date_str],
                point_count=int(count),
            )
        )

    return daily_stats_list


def build_survey_statistics(
    gdf_filtered: gpd.GeoDataFrame,
    original_count: int,
    threshold: pd.Timedelta,
    distance_col: str = "distance_m",
    deltatime_col: str = "deltatime",
) -> SurveyStatistics:
    """
    Construit l'objet SurveyStatistics complet.

    :param gdf_filtered: GeoDataFrame après filtrage.
    :type gdf_filtered: gpd.GeoDataFrame
    :param original_count: Nombre de points avant filtrage.
    :type original_count: int
    :param threshold: Seuil de filtrage appliqué.
    :type threshold: pd.Timedelta
    :param distance_col: Nom de la colonne distance.
    :type distance_col: str
    :param deltatime_col: Nom de la colonne deltatime.
    :type deltatime_col: str
    :return: Statistiques complètes du levé.
    :rtype: SurveyStatistics
    """
    # Stats journalières
    daily_stats = aggregate_daily_statistics(
        gdf_filtered, distance_col=distance_col, deltatime_col=deltatime_col
    )

    # Stats totales
    total_distance = compute_total_distance(gdf_filtered, col=distance_col)
    total_time = compute_total_time(gdf_filtered, col=deltatime_col)

    # Dates début/fin
    dt_index = pd.DatetimeIndex(gdf_filtered.index)
    start_date = dt_index.min().date().isoformat()
    end_date = dt_index.max().date().isoformat()

    # Points
    total_points = len(gdf_filtered)
    points_removed = original_count - total_points

    return SurveyStatistics(
        daily_stats=daily_stats,
        total_distance=total_distance,
        total_time=total_time,
        total_points=total_points,
        start_date=start_date,
        end_date=end_date,
        filtering_threshold=str(threshold),
        points_removed=points_removed,
    )
