from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Protocol, Optional

import pandas as pd


@dataclass(frozen=True)
class DataGapPeriod:
    start: datetime
    end: datetime
    duration: timedelta = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "duration", self.end - self.start)

    def __str__(self):
        return f"{self.start} - {self.end}"


class TimeSeriesProtocol(Protocol):
    WLO: str = "wlo"
    WLF_SPINE: str = "wlf-spine"
    WLF_VTG: str = "wlf-vtg"
    WLF: str = "wlf"
    WLP: str = "wlp"

    def from_str(cls, value: str):
        pass


class StationsHandlerProtocol(Protocol):
    def get_time_series_dataframe(
        self,
        station: str,
        from_time: str,
        to_time: str,
        time_serie_code: Optional[TimeSeriesProtocol],
        wlo_qc_flag_filter: Optional[list[str]],
    ) -> pd.DataFrame:
        pass
