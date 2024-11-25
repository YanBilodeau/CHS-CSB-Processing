from datetime import timedelta
from typing import Protocol, Optional


class EndpointTypeProtocol(Protocol):
    PUBLIC: str = "EndpointPublic"
    PRIVATE_PROD: str = "EndpointPrivateProd"
    PRIVATE_DEV: str = "EndpointPrivateDev"


class TimeSeriesProtocol(Protocol):
    WLO: str = "wlo"
    WLF_SPINE: str = "wlf-spine"
    WLF_VTG: str = "wlf-vtg"
    WLF: str = "wlf"
    WLP: str = "wlp"

    def from_str(cls, value: str):
        pass


class ResponseProtocol(Protocol):
    status_code: int
    is_ok: bool
    message: str
    error: str
    data: list[dict]


class IWLSapiProtocol(Protocol):
    def get_all_stations(self, **kwargs) -> ResponseProtocol:
        pass

    def get_time_series_station(self, station: str) -> ResponseProtocol:
        pass

    def get_metadata_station(self, station: str) -> ResponseProtocol:
        pass

    def get_time_serie_block_data(
        self,
        station: str,
        from_time: str,
        to_time: str,
        time_serie_code: Optional[TimeSeriesProtocol],
        time_delta: timedelta = timedelta(days=7),
        datetime_sorted: bool = True,
        **kwargs,
    ) -> ResponseProtocol:
        pass
