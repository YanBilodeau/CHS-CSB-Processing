from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from .exception_vessel import MissingConfigKeyError
from . import vessel_ids as ids
from .vessel_models import VesselConfigDict


class AxisConvention(StrEnum):
    """
    Enumération des conventions d'axes.

    CARIS (str): The X-Y-Z fields set the location from the Reference Point (0). The Reference Point is the point on
    the vessel where the X, Y, and Z axes intersect. The X, Y, and Z fields are defined as follows:
        •X: The athwart-ship distance of the sensor, positive to starboard.
        •Y: The along-ship distance of the sensor, positive to the bow.
        •Z: The vertical distance of the sensor, positive into the water.
    """

    CARIS: str = ids.CARIS


class Sensor(BaseModel):
    time_stamp: datetime
    x: float
    y: float
    z: float


class BDBattribute(BaseModel):
    time_stamp: datetime
    pltfrm: str
    sdghdw: str
    poshdw: str
    bureau: str
    restrn: str


class Waterline(BaseModel):
    time_stamp: datetime
    z: float


class SoundSpeedProfile(BaseModel):
    time_stamp: datetime
    ssp: bool


class VesselConfig(BaseModel):
    id: str
    axis_convention: AxisConvention
    navigation: list[Sensor]
    motion: list[Sensor]
    sounder: list[Sensor]
    waterline: list[Waterline]
    ssp_applied: list[SoundSpeedProfile]
    attribute: list[BDBattribute]


def get_vessel_config_from_config_dict(config: VesselConfigDict) -> VesselConfig:
    """
    Récupère la configuration du navire.

    :param config: (VesselConfigDict) Configuration du navire.
    :return: (VesselConfig) Configuration du navire.
    """
    required_keys = [
        ids.ID,
        ids.AXIS_CONVENTION,
        ids.NAV,
        ids.MOTION,
        ids.SOUNDER,
        ids.WATERLINE,
        ids.SSP_APPLIED,
        ids.ATTRIBUTE,
    ]
    missing_keys = [key for key in required_keys if key not in config]

    if missing_keys:
        raise MissingConfigKeyError(missing_keys=missing_keys)

    return VesselConfig(
        id=config[ids.ID],
        axis_convention=config[ids.AXIS_CONVENTION],
        navigation=[Sensor(**nav) for nav in config[ids.NAV]],
        motion=[Sensor(**motion) for motion in config[ids.MOTION]],
        sounder=[Sensor(**sounder) for sounder in config[ids.SOUNDER]],
        waterline=[Waterline(**waterline) for waterline in config[ids.WATERLINE]],
        ssp_applied=[SoundSpeedProfile(**ssp) for ssp in config[ids.SSP_APPLIED]],
        attribute=[BDBattribute(**attr) for attr in config[ids.ATTRIBUTE]],
    )
