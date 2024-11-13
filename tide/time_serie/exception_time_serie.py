from dataclasses import dataclass
from datetime import timedelta

import pandas as pd

from .time_serie_models import DataGapPeriod


@dataclass(frozen=True)
class WaterLevelDataError(Exception):
    station_id: str
    from_time: str
    to_time: str

    def __str__(self) -> str:
        return f"Aucune donnée n'a été récupérée pour la station '{self.station_id}' de {self.from_time} à {self.to_time}."


@dataclass(frozen=True)
class WaterLevelDataGapError(Exception):
    station_id: str
    gaps: pd.DataFrame
    max_time_gap: str

    def __str__(self) -> str:
        return (
            f"Il y a des périodes de données manquantes qui excède la limite permise de {self.max_time_gap} pour la"
            f" station {self.station_id}. {get_data_gaps_message(gaps=self.gaps)}"
        )


def get_data_gap_periods(gaps: pd.DataFrame) -> list[DataGapPeriod]:
    """
    Récupère les périodes de données manquantes.

    :param gaps: (pd.DataFrame) DataFrame contenant les périodes de données manquantes.
    :return: (list[DataGap]) Périodes de données manquantes.
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

    :param gaps: (pd.DataFrame) Périodes de données manquantes.
    :return: (str) Journalisation des périodes de données manquantes.
    """
    data_gaps_list: list[DataGapPeriod] = get_data_gap_periods(gaps=gaps)

    total_duration_minutes = (
        sum((gap.duration for gap in data_gaps_list), timedelta()).total_seconds() / 60
    )
    gaps_str = "; ".join([str(gap) for gap in data_gaps_list])

    return f"{total_duration_minutes} minutes de données manquantes pour les périodes suivantes : {gaps_str}."


@dataclass(frozen=True)
class InterpolationValueError(Exception):
    from_time: pd.Timestamp
    to_time: pd.Timestamp

    def __str__(self) -> str:
        return f"Impossible d'interpoler les valeurs de {self.from_time} à {self.to_time}. Il y a possiblement des données manquantes."
