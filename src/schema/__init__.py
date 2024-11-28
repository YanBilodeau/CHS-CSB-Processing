"""
Ce package contient les schémas des données.
"""

from .model import (
    DataLoggerSchema,
    DataLoggerWithTideZoneSchema,
    StationsSchema,
    TideZoneSchema,
    TimeSerieDataSchema,
    validate_schema,
)


__all__ = [
    "DataLoggerSchema",
    "StationsSchema",
    "TideZoneSchema",
    "TimeSerieDataSchema",
    "validate_schema",
]
