"""
Module contenant les exceptions pour les séries temporelles de données de marée.

Ce module contient les exceptions sont utilisées pour gérer les erreurs lors de la récupération des données de marée.
"""

from dataclasses import dataclass
from datetime import timedelta

import pandas as pd

from .time_serie_models import DataGapPeriod, TimeSeriesProtocol
from schema import model_ids as schema_ids


@dataclass(frozen=True)
class NoWaterLevelDataError(Exception):
    """
    Exception pour les erreurs de données de marée manquantes.

    :param station_id: Code de la station.
    :type station_id: str
    :param from_time: Date de début.
    :type from_time: str
    :param to_time: Date de fin.
    :type to_time: str
    """

    station_id: str
    """Code de la station."""
    from_time: str
    """Date de début."""
    to_time: str
    """Date de fin."""

    def __str__(self) -> str:
        return f"Aucune donnée n'a été récupérée pour la station '{self.station_id}' de {self.from_time} à {self.to_time}."


@dataclass(frozen=True)
class WaterLevelDataGapError(Exception):
    """
    Exception pour les périodes de données manquantes.

    :param station_id: Code de la station.
    :type station_id: str
    :param gaps: Périodes de données manquantes.
    :type gaps: pd.DataFrame
    :param max_time_gap: Limite permise pour les données
    :type max_time_gap: str
    """

    station_id: str
    """Code de la station."""
    gaps: pd.DataFrame
    """Périodes de données manquantes."""
    max_time_gap: str
    """Limite permise pour les données."""

    def __str__(self) -> str:
        return (
            f"Il y a des périodes de données manquantes qui excède la limite permise de {self.max_time_gap} pour la"
            f" station {self.station_id}. {get_data_gaps_message(gaps=self.gaps)}"
        )


def get_data_gap_periods(gaps: pd.DataFrame) -> list[DataGapPeriod]:
    """
    Récupère les périodes de données manquantes.

    :param gaps: DataFrame contenant les périodes de données manquantes.
    :type gaps: pd.DataFrame
    :return: Périodes de données manquantes.
    :rtype: list[DataGapPeriod]
    """
    return [
        DataGapPeriod(
            start=row["event_date"] - row["data_time_gap"], end=row["event_date"]
        )
        for index, row in gaps.iterrows()
    ]


def get_data_gaps_message(gaps: pd.DataFrame) -> str:
    """
    Journalise les périodes de données manquantes.

    :param gaps: Périodes de données manquantes.
    :type gaps: pd.DataFrame
    :return: Journalisation des périodes de données manquantes.
    :rtype: str
    """
    data_gaps_list: list[DataGapPeriod] = get_data_gap_periods(gaps=gaps)

    total_duration_minutes = (
        sum((gap.duration for gap in data_gaps_list), timedelta()).total_seconds() / 60
    )

    return f"{total_duration_minutes} minutes de données manquantes {gaps.attrs.get(schema_ids.NAME_METADATA)}."


@dataclass(frozen=True)
class InterpolationValueError(Exception):
    """
    Exception pour les valeurs impossibles à interpoler.

    :param from_time: Date de début.
    :type from_time: pd.Timestamp
    :param to_time: Date de fin.
    :type to_time: pd.Timestamp
    :param time_serie: Série temporelle.
    :type time_serie: TimeSeriesProtocol
    """

    from_time: pd.Timestamp
    """Date de début."""
    to_time: pd.Timestamp
    """Date de fin."""
    time_serie: TimeSeriesProtocol
    """Série temporelle."""

    def __str__(self) -> str:
        return (
            f"Impossible d'interpoler les valeurs de {self.from_time} à {self.to_time} pour la série temporelle "
            f"{self.time_serie}. Il manque des données pour réaliser l'interpolation."
        )
