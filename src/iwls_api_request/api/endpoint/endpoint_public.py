from dataclasses import dataclass

from .endpoint_abc import Endpoint
from .. import ids_iwls as ids
from ..models_api import EndpointType


@dataclass(frozen=True, slots=True)
class EndpointPublic(Endpoint):
    """
    Classe pour les points d'entrés de l'API publique.
    """
    API: str = r"https://api-iwls.dfo-mpo.gc.ca/api/v1/"
    TYPE: EndpointType = EndpointType.PUBLIC
    BENCHMARK: str = f"benchmarks/{{{ids.BENCHMARK}}}"
    BENCHMARKS: str = "benchmarks"
    BENCHMARK_METADATA: str = f"benchmarks/{{{ids.BENCHMARK}}}/metadata"
    ELEVVATIONS: str = f"benchmarks/{{{ids.BENCHMARK}}}/elevations"
    HEIGHT_TYPE: str = f"height-types/{{{ids.HEIGHT_TYPE}}}"
    HEIGHT_TYPES: str = "height-types"
    PHENOMENA: str = "phenomena"
    PHENOMENON: str = f"phenomena/{{{ids.PHENOMENON}}}"
    STATION: str = f"stations/{{{ids.STATION}}}"
    STATIONS: str = "stations"
    STATION_DATA: str = f"stations/{{{ids.STATION}}}/data"
    STATION_DATA_LATEST: str = "stations/data/latest"
    STATION_METADATA: str = f"stations/{{{ids.STATION}}}/metadata"
    STATION_STATS_DAILY: str = f"stations/{{{ids.STATION}}}/stats/calculate-daily-means"
    STATION_STATS_MONTHLY: str = (
        f"stations/{{{ids.STATION}}}/stats/calculate-monthly-mean"
    )
    TIDE_TABLE: str = f"tide-tables/{{{ids.TIDE_TABLE}}}"
    TIDE_TABLES: str = "tide-tables"
    TIME_SERIES_DEFINITION: str = "time-series-definitions/"
    TIME_SERIE_DEFINITION: str = (
        f"time-series-definitions/{{{ids.TIME_SERIES_DEFINITION_ID}}}"
    )
