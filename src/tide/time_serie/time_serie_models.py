"""
Module contenant les modèles pour les séries temporelles de données de marée.

Ce module contient les modèles de données et les protocoles pour les séries temporelles de données de marée.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Protocol, Optional, runtime_checkable

import pandas as pd


@dataclass(frozen=True)
class DataGapPeriod:
    """
    Modèle pour les périodes de données manquantes.

    :param start: Date de début.
    :type start: datetime
    :param end: Date de fin.
    :type end: datetime
    :param duration: Durée de la période.
    :type duration: timedelta
    """

    start: datetime
    """Date de début."""
    end: datetime
    """Date de fin."""
    duration: timedelta = field(init=False)
    """Durée de la période."""

    def __post_init__(self):
        object.__setattr__(self, "duration", self.end - self.start)

    def __str__(self):
        return f"{self.start} - {self.end}"


@runtime_checkable
class TimeSeriesProtocol(Protocol):
    """
    Protocole pour définir les types des séries temporelles.
    """

    WLO: str = "wlo"
    """Water Level Observed."""
    WLF_SPINE: str = "wlf-spine"
    """Water Level Forecast Spine."""
    WLF_VTG: str = "wlf-vtg"
    """Water Level Forecast VTG."""
    WLF: str = "wlf"
    """Water Level Forecast."""
    WLP: str = "wlp"
    """Water Level Prediction."""

    def from_str(cls, value: str) -> "TimeSeriesProtocol":
        """
        Méthode pour convertir une chaîne de caractères en série temporelle.

        :param value: Chaîne de caractères.
        :type value: str
        :return: Série temporelle.
        :rtype: TimeSeriesProtocol
        """
        pass


class StationsHandlerProtocol(Protocol):
    """
    Protocole pour les gestionnaires de stations.
    """

    def get_time_series_dataframe(
        self,
        station: str,
        from_time: str,
        to_time: str,
        time_serie_code: Optional[TimeSeriesProtocol],
        wlo_qc_flag_filter: Optional[list[str]],
    ) -> pd.DataFrame:
        """
        Méthode pour récupérer les données de marée d'une station.

        :param station: Code de la station.
        :type station: str
        :param from_time: Date de début.
        :type from_time: str
        :param to_time: Date de fin.
        :type to_time: str
        :param time_serie_code: Code de la série temporelle.
        :type time_serie_code: TimeSeriesProtocol
        :param wlo_qc_flag_filter: Flag de qualité à filtrer.
        :type wlo_qc_flag_filter: list[str]
        :return: Données de marée.
        :rtype: pd.DataFrame
        """
        pass

    @property
    def stations(self) -> list[dict]:
        """
        Propriété pour obtenir les stations.

        :return: Stations.
        :rtype: list[dict]
        """
        pass
