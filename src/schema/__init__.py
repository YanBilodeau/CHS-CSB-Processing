"""
Ce package contient les schémas des données.
"""

from .model import (
    DataLoggerSchema,
    DataLoggerWithTideZoneSchema,
    DataLoggerWithVoronoiSchema,
    StationsSchema,
    TideZoneProtocolSchema,
    TideZoneStationSchema,
    TideZoneInfoSchema,
    WaterLevelSerieDataSchema,
    WaterLevelSerieDataWithMetaDataSchema,
    validate_schema,
    validate_schemas,
    WaterLevelInfo,
    OutlierInfo,
    Status,
)


__all__ = [
    "DataLoggerSchema",
    "DataLoggerWithTideZoneSchema",
    "DataLoggerWithVoronoiSchema",
    "StationsSchema",
    "TideZoneProtocolSchema",
    "TideZoneStationSchema",
    "WaterLevelSerieDataSchema",
    "TideZoneInfoSchema",
    "WaterLevelSerieDataWithMetaDataSchema",
    "validate_schema",
    "validate_schemas",
    "WaterLevelInfo",
    "OutlierInfo",
    "Status",
]
