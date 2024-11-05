from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from .vessel_model import VesselConfigDict


class AxisConvention(StrEnum):
    """
    Enumération des conventions d'axes.

    CARIS (str): The X-Y-Z fields set the location from the Reference Point (0). The Reference Point is the point on
    the vessel where the X, Y, and Z axes intersect. The X, Y, and Z fields are defined as follows:
        •X: The athwart-ship distance of the sensor, positive to starboard.
        •Y: The along-ship distance of the sensor, positive to the bow.
        •Z: The vertical distance of the sensor, positive into the water.
    """

    CARIS: str = "CARIS"


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
    logger_id: str
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
    return VesselConfig(
        id=config["id"],
        logger_id=config["logger_id"],
        axis_convention=config["axis_convention"],
        navigation=[Sensor(**nav) for nav in config["nav"]],
        motion=[Sensor(**motion) for motion in config["motion"]],
        sounder=[Sensor(**sounder) for sounder in config["sounder"]],
        waterline=[Waterline(**waterline) for waterline in config["waterline"]],
        ssp_applied=[SoundSpeedProfile(**ssp) for ssp in config["ssp_applied"]],
        attribute=[BDBattribute(**attr) for attr in config["attribute"]],
    )
