from dataclasses import dataclass

import pandas as pd

from .time_serie_dataframe import get_data_gaps_message


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
