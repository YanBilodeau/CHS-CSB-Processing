"""
Ce package contient les fonctions et les classes nécessaires pour traiter les séries temporelles.
"""

from .exception_time_serie import (
    WaterLevelDataGapError,
    NoWaterLevelDataError,
    InterpolationValueError,
)
from .time_serie_dataframe import (
    get_water_level_data_for_stations,
)


__all__ = [
    "get_water_level_data_for_stations",
    "WaterLevelDataGapError",
    "NoWaterLevelDataError",
    "InterpolationValueError",
]
