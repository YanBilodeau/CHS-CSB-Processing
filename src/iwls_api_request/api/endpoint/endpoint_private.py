from abc import ABC
from dataclasses import dataclass

from .endpoint_abc import Endpoint
from .. import ids_iwls as ids
from ..models_api import EndpointType


@dataclass(frozen=True, slots=True)
class EndpointPrivate(Endpoint, ABC):
    BENCHMARK: str = f"benchmarks/{{{ids.BENCHMARK}}}"
    BENCHMARKS: str = "benchmarks/"
    BENCHMARK_METADATA: str = f"benchmarks/{{{ids.BENCHMARK}}}/metadata"
    ELEVVATIONS: str = f"benchmarks/{{{ids.BENCHMARK}}}/elevations"
    GNSS_STATION: str = f"stations/{{{ids.STATION}}}/gnss/{{{ids.GNSS}}}"
    GNSS_STATIONS: str = f"stations/{{{ids.STATION}}}/gnss"
    GNSS_SUM: str = f"stations/{{{ids.STATION}}}/gnss/{{{ids.GNSS}}}/sum"
    HEIGHT_TYPE: str = f"heights/{{{ids.HEIGHT_TYPE}}}"
    HEIGHT_TYPES: str = "heights/"
    PHENOMENA: str = "phenomena/"
    PHENOMENON: str = f"phenomena/{{{ids.PHENOMENON}}}"
    REGIONS: str = "chsRegions/"
    STATION: str = f"stations/{{{ids.STATION}}}"
    STATIONS: str = "stations/"
    STATION_DATA: str = f"stations/{{{ids.STATION}}}/time-series/{{{ids.TS}}}/data"
    STATION_METADATA: str = f"stations/{{{ids.STATION}}}/metadata"
    STATION_TIME_SERIES: str = f"stations/{{{ids.STATION}}}/time-series/"
    TIDE_TABLE: str = f"tideTables/{{{ids.TIDE_TABLE}}}"
    TIDE_TABLES: str = "tideTables/"
    TIME_SERIES_DEFINITION: str = "time-series-definitions/"
    TIME_SERIE_DEFINITION: str = f"time-series-definitions/{{{ids.ID}}}"


@dataclass(frozen=True, slots=True)
class EndpointPrivateDev(EndpointPrivate):
    """
    Classe pour les points d'entrés de l'API privée de développement.
    """

    API: str = ""
    TYPE: EndpointType = EndpointType.PRIVATE_DEV


@dataclass(frozen=True, slots=True)
class EndpointPrivateProd(EndpointPrivate):
    """
    Classe pour les points d'entrés de l'API privée de production.
    """

    API: str = ""
    TYPE: EndpointType = EndpointType.PRIVATE_PROD
