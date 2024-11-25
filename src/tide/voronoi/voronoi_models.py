from typing import Protocol, Collection, Optional

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
        filter_time_series: Collection[TimeSeriesProtocol] | None,
        exclude_stations: Collection[str] | None,
        ttl: Optional[int],
    ) -> gpd.GeoDataFrame:
        pass
