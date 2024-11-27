from abc import ABC
from dataclasses import dataclass
from typing import Optional

from ..models_api import EndpointType


@dataclass(frozen=True, slots=True)
class Endpoint(ABC):
    """
    Classe abstraite pour les points d'entrés de l'API.

    :param API: URL de l'API.
    :param TYPE: Type de l'API.
    :param BENCHMARK: Point d'entrée pour un repère.
    :param BENCHMARKS: Point d'entrée pour les repères.
    :param BENCHMARK_METADATA: Point d'entrée pour les métadonnées d'un repère.
    :param ELEVVATIONS: Point d'entrée pour les élévations d'un repère.
    :param HEIGHT_TYPE: Point d'entrée pour un type de hauteur.
    :param HEIGHT_TYPES: Point d'entrée pour les types de hauteurs.
    :param PHENOMENA: Point d'entrée pour les phénomènes.
    :param PHENOMENON: Point d'entrée pour un phénomène.
    :param STATION: Point d'entrée pour une station.
    :param STATIONS: Point d'entrée pour les stations.
    :param STATION_DATA: Point d'entrée pour les données d'une station.
    :param STATION_METADATA: Point d'entrée pour les métadonnées d'une station.
    :param TIDE_TABLE: Point d'entrée pour une table des marées.
    :param TIDE_TABLES: Point d'entrée pour les tables des marées.
    :param TIME_SERIES_DEFINITION: Point d'entrée pour les définitions de séries temporelles.
    :param TIME_SERIE_DEFINITION: Point d'entrée pour une définition de série temporelle.
    :param GNSS_STATION: Point d'entrée pour une station GNSS.
    :param GNSS_STATIONS: Point d'entrée pour les stations GNSS.
    :param GNSS_SUM: Point d'entrée pour le sommaire des données GNSS.
    :param REGIONS: Point d'entrée pour les régions.
    :param STATION_DATA_LATEST: Point d'entrée pour les dernières données d'une station.
    :param STATION_TIME_SERIES: Point d'entrée pour les séries temporelles d'une station.
    :param STATION_STATS_DAILY: Point d'entrée pour les statistiques journalières d'une station.
    :param STATION_STATS_MONTHLY: Point d'entrée pour les statistiques mensuelles d'une station.
    """

    API: str
    TYPE: EndpointType
    BENCHMARK: str
    BENCHMARKS: str
    BENCHMARK_METADATA: str
    ELEVVATIONS: str
    HEIGHT_TYPE: str
    HEIGHT_TYPES: str
    PHENOMENA: str
    PHENOMENON: str
    STATION: str
    STATIONS: str
    STATION_DATA: str
    STATION_METADATA: str
    TIDE_TABLE: str
    TIDE_TABLES: str
    TIME_SERIES_DEFINITION: str
    TIME_SERIE_DEFINITION: str
    GNSS_STATION: Optional[str] = None
    GNSS_STATIONS: Optional[str] = None
    GNSS_SUM: Optional[str] = None
    REGIONS: Optional[str] = None
    STATION_DATA_LATEST: Optional[str] = None
    STATION_TIME_SERIES: Optional[str] = None
    STATION_STATS_DAILY: Optional[str] = None
    STATION_STATS_MONTHLY: Optional[str] = None
