"""
Ce package contient les schémas des données.
"""

from .model import (
    DataLoggerSchema,
    StationsSchema,
    TideZoneSchema,
    TimeSerieDataSchema,
    validate_schema,
)
from .model_ids import TIME_UTC, LATITUDE_WGS84, LONGITUDE_WGS84, DEPTH_METER

__all__ = [
    "DataLoggerSchema",
    "StationsSchema",
    "TideZoneSchema",
    "TimeSerieDataSchema",
    "validate_schema",
    "TIME_UTC",
    "LATITUDE_WGS84",
    "LONGITUDE_WGS84",
    "DEPTH_METER",
]
