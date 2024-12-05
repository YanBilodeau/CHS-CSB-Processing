"""
Ce package contient les schémas des données.
"""

from .model import (
    DataLoggerSchema,
    DataLoggerWithTideZoneSchema,
    DataLoggerProcessedSchema,
    DataLoggerProcessedSchemaWithTideZone,
    StationsSchema,
    TideZoneProtocolSchema,
    TideZoneStationSchema,
    TideZoneInfoSchema,
    WaterLevelSerieDataSchema,
    WaterLevelSerieDataWithMetaDataSchema,
    validate_schema,
    validate_schemas,
)


__all__ = [
    "DataLoggerSchema",
    "DataLoggerWithTideZoneSchema",
    "DataLoggerProcessedSchema",
    "DataLoggerProcessedSchemaWithTideZone",
    "StationsSchema",
    "TideZoneProtocolSchema",
    "TideZoneStationSchema",
    "WaterLevelSerieDataSchema",
    "TideZoneInfoSchema",
    "WaterLevelSerieDataWithMetaDataSchema",
    "validate_schema",
    "validate_schemas",
]
