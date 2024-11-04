from typing import Protocol

import geopandas as gpd


class TimeSeriesProtocol(Protocol):
    WLO: str
    WLF_SPINE: str
    WLF: str
    WLP: str

    def from_str(cls, value: str):
        pass


class StationsHandlerProtocol(Protocol):
    def get_stations_geodataframe(
        self,
        filter_time_series: list[TimeSeriesProtocol] | None,
        **kwargs,
    ) -> gpd.GeoDataFrame:
        pass
