"""
Ce package contient les classes et les fonctions qui permettent de manipuler les données des navires.
"""

from .vessel_config import VesselConfig, AxisConvention, Sensor, BDBattribute, Waterline, SoundSpeedProfile
from .vessel_config_json_manager import VesselConfigJsonManager


__all__ = ['VesselConfig', 'AxisConvention', 'Sensor', 'BDBattribute', 'Waterline', 'SoundSpeedProfile', 'VesselConfigJsonManager']
