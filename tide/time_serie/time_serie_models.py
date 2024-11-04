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
    WLO: str
    WLF_SPINE: str
    WLF: str
    WLP: str

    def from_str(cls, value: str):
        pass


class StationsHandlerProtocol(Protocol):
    def get_time_series_dataframe(
        self,
        station: str,
        from_time: str,
        to_time: str,
        time_serie_code: Optional[TimeSeriesProtocol],
    ) -> pd.DataFrame:
        pass
