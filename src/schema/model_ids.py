"""
Ce module contient les constantes pour les identifiants des modèles de données.
"""

# Constantes pour les noms des colonnes des données du schéma de données DataLoggerSchema.
TIME_UTC: str = "Time_UTC"
"""Valeur de la constante Time_UTC."""
DEPTH_RAW_METER: str = "Depth_raw_meter"
"""Valeur de la constante Depth_raw_meter."""
LONGITUDE_WGS84: str = "Longitude_WGS84"
"""Valeur de la constante Longitude_WGS84."""
LATITUDE_WGS84: str = "Latitude_WGS84"
"""Valeur de la constante Latitude_WGS84."""
GEOMETRY: str = "geometry"
"""Valeur de la constante geometry."""

# Constantes pour les noms des colonnes des données du schéma de données DataLoggerWithTideZoneSchema.
TIDE_ZONE_ID: str = "Tide_zone_id"
"""Valeur de la constante Tide_zone_id."""

# Constantes pour les noms des colonnes des données du schéma de données DataLoggerProcessedZoneSchema.
DEPTH_PROCESSED_METER: str = "Depth_processed_meter"
"""Valeur de la constante Depth_processed_meter."""
WATER_LEVEL_METER: str = "Water_level_meter"
"""Valeur de la constante Water_level_meter."""
UNCERTAINTY: str = "Uncertainty"
"""Valeur de la constante Uncertainty."""

# Constantes pour les noms des colonnes des données du schéma de données StationsSchema et TideZoneSchema.
ID: str = "id"
"""Valeur de la constante id."""
CODE: str = "code"
"""Valeur de la constante code."""
NAME: str = "name"
"""Valeur de la constante name."""
TIME_SERIES: str = "time_series"
"""Valeur de la constante time_series."""
IS_TIDAL: str = "is_tidal"
"""Valeur de la constante is_tidal."""

# Constantes pour les noms des colonnes des données du schéma de données TimeSerieDataSchema.
EVENT_DATE: str = "event_date"
"""Valeur de la constante event_date."""
VALUE: str = "value"
"""Valeur de la constante value."""
TIME_SERIE_CODE: str = "time_serie_code"
"""Valeur de la constante time_serie_code."""

# Constantes pour les noms des colonnes des données du schéma de données TimeSerieDataWithMetaDataSchema.
NAME_METADATA: str = "name"
"""Valeur de la constante name."""
STATION_ID: str = "station_id"
"""Valeur de la constante station_id."""
START_TIME: str = "start_time"
"""Valeur de la constante start_time."""
END_TIME: str = "end_time"
"""Valeur de la constante end_time."""

# Constantes pour les noms des colonnes des données du schéma de données TideZoneSchema.
MIN_TIME: str = "min_time"
"""Valeur de la constante min_time."""
MAX_TIME: str = "max_time"
"""Valeur de la constante max_time."""
