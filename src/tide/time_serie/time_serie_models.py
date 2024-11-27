"""
Module contenant les modèles pour les séries temporelles de données de marée.

Ce module contient les modèles de données pour les séries temporelles de données de marée.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Protocol, Optional

import pandas as pd


@dataclass(frozen=True)
class DataGapPeriod:
    """
    Modèle pour les périodes de données manquantes.

    :param start: (datetime) Date de début.
    :param end: (datetime) Date de fin.
    :param duration: (timedelta) Durée de la période.
    """

    start: datetime
    end: datetime
    duration: timedelta = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "duration", self.end - self.start)

    def __str__(self):
        return f"{self.start} - {self.end}"


class TimeSeriesProtocol(Protocol):
    """
    Protocole pour définir les types des séries temporelles.

    :param WLO: Water Level Observed.
    :param WLF_SPINE: Water Level Forecast Spine.
    :param WLF_VTG: Water Level Forecast VTG.
    :param WLF: Water Level Forecast.
    :param WLP: Water Level Prediction.
    """

    WLO: str = "wlo"
    WLF_SPINE: str = "wlf-spine"
    WLF_VTG: str = "wlf-vtg"
    WLF: str = "wlf"
    WLP: str = "wlp"

    def from_str(cls, value: str):
        """
        Méthode pour convertir une chaîne de caractères en série temporelle.
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

        :param station: (str) Code de la station.
        :param from_time: (str) Date de début.
        :param to_time: (str) Date de fin.
        :param time_serie_code: (TimeSeriesProtocol) Code de la série temporelle.
        :param wlo_qc_flag_filter: (list[str]) Flag de qualité à filtrer.
        :return: (pd.DataFrame) Données de marée.
        """
        pass
