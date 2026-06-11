"""
Module de statistiques de levé bathymétrique.

Calcule distance et temps de sondage par jour avec gestion
des frontières de journée UTC.

Usage::

    from metadata.statistic import compute_survey_statistics
    import geopandas as gpd
    import pandas as pd

    # Charger données
    gdf = gpd.read_file("survey.gpkg")

    # Calculer stats
    stats = compute_survey_statistics(
        gdf,
        deltatime_threshold=pd.Timedelta("1min"),
        reset_boundaries=True,
    )

    # Accéder aux résultats
    print(f"Distance totale : {stats.total_distance.kilometers} km")
    print(f"Temps total : {stats.total_time.total_hours} h")
    print(f"Points filtrés : {stats.points_removed}")

    for day in stats.daily_stats:
        print(f"{day.date} : {day.distance.nautical_miles} NM, {day.time.total_hours} h")
"""

from .models import DailyStats, DistanceStats, SurveyStatistics, TimeStats
from .pipeline import compute_survey_statistics

__all__ = [
    "compute_survey_statistics",
    "SurveyStatistics",
    "DailyStats",
    "DistanceStats",
    "TimeStats",
]
