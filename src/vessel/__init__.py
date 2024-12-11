"""
Ce package contient les classes et les fonctions qui permettent de manipuler les données des navires.
"""

from .vessel_config import (
    VesselConfig,
    AxisConvention,
    Sensor,
    BDBattribute,
    Waterline,
    SoundSpeedProfile,
)
from .vessel_config_json_manager import VesselConfigJsonManager
from .vessel_config_sqlite_manager import VesselConfigSQLiteManager
from .vessel_config_manager_abc import VesselConfigManagerABC
from .factory_vessel_config_manager import (
    VesselConfigManagerType,
    get_vessel_config_manager_factory,
)


__all__ = [
    "VesselConfig",
    "AxisConvention",
    "Sensor",
    "BDBattribute",
    "Waterline",
    "SoundSpeedProfile",
    "VesselConfigJsonManager",
    "VesselConfigSQLiteManager",
    "VesselConfigManagerABC",
    "VesselConfigManagerType",
    "get_vessel_config_manager_factory",
]
