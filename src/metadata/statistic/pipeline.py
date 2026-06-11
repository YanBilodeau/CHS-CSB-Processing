"""
Pipeline principal de calcul des statistiques de levé.

Ce module orchestre le workflow complet : validation CRS, enrichissement
des colonnes, filtrage et agrégation des statistiques.
"""

import geopandas as gpd
import pandas as pd

from .boundary_handler import reset_day_boundaries, reset_implausible_distances
from .crs_operations import validate_and_normalize_crs
from .distance_calculator import add_distance_column
from .filters import DeltatimeFilter
from .models import SurveyStatistics
from .statistics_aggregator import build_survey_statistics
from .temporal_operations import add_deltatime_column, set_datetime_index


def compute_survey_statistics(
    gdf: gpd.GeoDataFrame,
    *,
    time_column: str = "Time_UTC",
    deltatime_threshold: pd.Timedelta = pd.Timedelta("1min"),
    reset_boundaries: bool = True,
) -> SurveyStatistics:
    """
    Calcule les statistiques complètes d'un levé bathymétrique.

    Pipeline complet :
      1. Validation et normalisation CRS (WGS84)
      2. Index temporel (DatetimeIndex UTC trié)
      3. Calcul deltatime (temps entre points)
      4. Calcul distance (mètres entre points)
      5. (Optionnel) Neutralisation frontières de journée
      6. Neutralisation distances implausibles (multi-capteurs simultanés)
      7. Filtrage par deltatime
      8. Agrégation statistiques (distance + temps par jour)

    :param gdf: GeoDataFrame avec colonnes Time_UTC et geometry.
    :type gdf: gpd.GeoDataFrame
    :param time_column: Nom de la colonne temporelle.
    :type time_column: str
    :param deltatime_threshold: Seuil max de deltatime accepté.
    :type deltatime_threshold: pd.Timedelta
    :param reset_boundaries: Neutraliser trajets retour au port ?
    :type reset_boundaries: bool
    :return: Statistiques complètes du levé.
    :rtype: SurveyStatistics
    :raises ValueError: Si le GeoDataFrame n'a pas de CRS.
    :raises KeyError: Si la colonne temporelle est absente.
    """
    # 1. Validation CRS
    gdf = validate_and_normalize_crs(gdf)

    # 2. Index temporel
    gdf = set_datetime_index(gdf, time_column)

    # 3. Colonnes dérivées
    gdf = add_deltatime_column(gdf)
    gdf = add_distance_column(gdf)

    # 4. (Optionnel) Reset frontières de journée
    if reset_boundaries:
        gdf = reset_day_boundaries(gdf)

    # 5. Distances physiquement impossibles (multi-capteurs simultanés)
    gdf = reset_implausible_distances(gdf)

    # 6. Filtrage
    original_count = len(gdf)
    filter_obj = DeltatimeFilter(deltatime_threshold)
    gdf_filtered = filter_obj.apply(gdf)

    # 6. Agrégation
    stats = build_survey_statistics(gdf_filtered, original_count, deltatime_threshold)

    return stats
