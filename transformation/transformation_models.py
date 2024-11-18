from typing import Protocol, Optional


class DataFilterConfigProtocol(Protocol):
    min_latitude: int | float
    max_latitude: int | float
    min_longitude: int | float
    max_longitude: int | float
    min_depth: int | float
    max_depth: Optional[int | float]