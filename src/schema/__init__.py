"""
Ce package contient les schémas des données.
"""

from .model import (
    DataLoggerSchema,
    DataLoggerWithTideZoneSchema,
    StationsSchema,
    TideZoneProtocolSchema,
    TideZoneSchema,
    TimeSerieDataSchema,
    validate_schema,
)


__all__ = [
    "DataLoggerSchema",
    "StationsSchema",
    "TideZoneProtocolSchema",
    "TideZoneSchema",
    "TimeSerieDataSchema",
    "validate_schema",
]
