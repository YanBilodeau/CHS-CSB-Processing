"""
Ce package contient les schémas des données.
"""

from .model import (
    DataLoggerSchema,
    DataLoggerWithTideZoneSchema,
    StationsSchema,
    TideZoneProtocolSchema,
    TideZoneStationSchema,
    TideZoneInfoSchema,
    WaterLevelSerieDataSchema,
    WaterLevelSerieDataWithMetaDataSchema,
    validate_schema,
    validate_schemas,
    WaterLevelInfo,
)


__all__ = [
    "DataLoggerSchema",
    "DataLoggerWithTideZoneSchema",
    "StationsSchema",
    "TideZoneProtocolSchema",
    "TideZoneStationSchema",
    "WaterLevelSerieDataSchema",
    "TideZoneInfoSchema",
    "WaterLevelSerieDataWithMetaDataSchema",
    "validate_schema",
    "validate_schemas",
    "WaterLevelInfo",
]
