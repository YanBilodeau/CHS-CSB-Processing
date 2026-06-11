"""
Modèles de données pour les statistiques de levé bathymétrique.

Ce module définit les dataclasses immuables pour représenter
les statistiques de distance, temps et récapitulatifs journaliers/totaux.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DistanceStats:
    """
    Statistiques de distance pour une période.

    :param meters: Distance en mètres.
    :type meters: float
    :param kilometers: Distance en kilomètres.
    :type kilometers: float
    :param nautical_miles: Distance en milles nautiques.
    :type nautical_miles: float
    """

    meters: float
    kilometers: float
    nautical_miles: float


@dataclass(frozen=True, slots=True)
class TimeStats:
    """
    Statistiques de temps pour une période.

    :param total_seconds: Durée totale en secondes.
    :type total_seconds: float
    :param total_minutes: Durée totale en minutes.
    :type total_minutes: float
    :param total_hours: Durée totale en heures.
    :type total_hours: float
    :param total_days: Durée totale en jours.
    :type total_days: float
    """

    total_seconds: float
    total_minutes: float
    total_hours: float
    total_days: float


@dataclass(frozen=True, slots=True)
class DailyStats:
    """
    Statistiques pour une journée UTC.

    :param date: Date au format ISO (YYYY-MM-DD).
    :type date: str
    :param distance: Statistiques de distance pour la journée.
    :type distance: DistanceStats
    :param time: Statistiques de temps pour la journée.
    :type time: TimeStats
    :param point_count: Nombre de points pour la journée.
    :type point_count: int
    """

    date: str
    distance: DistanceStats
    time: TimeStats
    point_count: int


@dataclass(frozen=True, slots=True)
class SurveyStatistics:
    """
    Statistiques complètes d'un levé bathymétrique.

    :param daily_stats: Liste des statistiques journalières.
    :type daily_stats: list[DailyStats]
    :param total_distance: Distance totale du levé.
    :type total_distance: DistanceStats
    :param total_time: Temps total de sondage.
    :type total_time: TimeStats
    :param total_points: Nombre total de points.
    :type total_points: int
    :param start_date: Date de début au format ISO.
    :type start_date: str
    :param end_date: Date de fin au format ISO.
    :type end_date: str
    :param filtering_threshold: Seuil de filtrage deltatime (ex: "1min").
    :type filtering_threshold: str
    :param points_removed: Nombre de points filtrés.
    :type points_removed: int
    """

    daily_stats: list[DailyStats]
    total_distance: DistanceStats
    total_time: TimeStats
    total_points: int
    start_date: str
    end_date: str
    filtering_threshold: str
    points_removed: int
