"""
Ce package contient les fonctions et les classes nécessaires pour traiter les séries temporelles.
"""

from .exception_time_serie import (
    WaterLevelDataGapError,
    WaterLevelDataError,
    InterpolationValueError,
    get_data_gaps_message,
)
from .time_serie_dataframe import (
    get_time_series_data,
    process_gaps_to_fill,
    get_water_level_data,
    identify_data_gaps,
)


__all__ = [
    "get_time_series_data",
    "process_gaps_to_fill",
    "get_water_level_data",
    "identify_data_gaps",
    "get_data_gaps_message",
    "WaterLevelDataGapError",
    "WaterLevelDataError",
    "InterpolationValueError",
]
