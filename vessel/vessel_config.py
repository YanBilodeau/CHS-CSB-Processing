from datetime import datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel

from .exception_vessel import MissingConfigKeyError, SensorNotFoundError
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

    def get_sensor(
        self, sensor_name: str, timestamp: datetime
    ) -> Sensor | Waterline | SoundSpeedProfile | BDBattribute:
        """
        Récupère les données d'un type de capteur à un instant donné.

        :param sensor_name: (str) Nom du capteur.
        :param timestamp: (datetime) Une date et heure.
        :return: (Sensor | Waterline | SoundSpeedProfile | BDBattribute) Données du capteur pour le moment donné.
        """
        sensors: list[Sensor | Waterline | SoundSpeedProfile | BDBattribute] = getattr(
            self, sensor_name
        )
        closest_sensor: Sensor | Waterline | SoundSpeedProfile | BDBattribute | None = (
            None
        )
        closest_time_diff: timedelta | None = None

        for sensor in sensors:
            time_diff: timedelta = timestamp - sensor.time_stamp
            if time_diff.total_seconds() >= 0 and (
                closest_time_diff is None or time_diff < closest_time_diff
            ):
                closest_sensor = sensor
                closest_time_diff = time_diff

        if closest_sensor is None:
            raise SensorNotFoundError(sensor_name=sensor_name, timestamp=timestamp)

        return closest_sensor

    def get_navigation(self, timestamp: datetime) -> Sensor:
        """
        Méthode pour récupérer les données de navigation à un instant donné.

        :param timestamp: (datetime) Une date et heure.
        :return: (Sensor) Données de navigation pour le moment donné.
        """
        return self.get_sensor(sensor_name=ids.NAVIGATION, timestamp=timestamp)

    def get_motion(self, timestamp: datetime) -> Sensor:
        """
        Méthode pour récupérer les données de mouvement à un instant donné.

        :param timestamp: (datetime) Une date et heure.
        :return: (Sensor) Données de mouvement pour le moment donné.
        """
        return self.get_sensor(sensor_name=ids.MOTION, timestamp=timestamp)

    def get_sounder(self, timestamp: datetime) -> Sensor:
        """
        Méthode pour récupérer les données du sondeur à un instant donné.

        :param timestamp: (datetime) Une date et heure.
        :return: (Sensor) Données du sondeur pour le moment donné.
        """
        return self.get_sensor(sensor_name=ids.SOUNDER, timestamp=timestamp)

    def get_waterline(self, timestamp: datetime) -> Waterline:
        """
        Méthode pour récupérer les données de ligne d'eau à un instant donné.

        :param timestamp: (datetime) Une date et heure.
        :return: (Waterline) Données de ligne d'eau pour le moment donné.
        """
        return self.get_sensor(sensor_name=ids.WATERLINE, timestamp=timestamp)

    def get_ssp_applied(self, timestamp: datetime) -> SoundSpeedProfile:
        """
        Méthode pour récupérer les données de profil de vitesse du son appliqué à un instant donné.

        :param timestamp: (datetime) Une date et heure.
        :return: (SoundSpeedProfile) Données de profil de vitesse du son appliqué pour le moment donné.
        """
        return self.get_sensor(sensor_name=ids.SSP_APPLIED, timestamp=timestamp)

    def get_attribute(self, timestamp: datetime) -> BDBattribute:
        """
        Méthode pour récupérer les données d'attribut à un instant donné.

        :param timestamp: (datetime) Une date et heure.
        :return: (BDBattribute) Données d'attribut pour le moment donné.
        """
        return self.get_sensor(sensor_name=ids.ATTRIBUTE, timestamp=timestamp)


def get_vessel_config_from_config_dict(config: VesselConfigDict) -> VesselConfig:
    """
    Récupère la configuration du navire.

    :param config: (VesselConfigDict) Configuration du navire.
    :return: (VesselConfig) Configuration du navire.
    """
    required_keys = [
        ids.ID,
        ids.AXIS_CONVENTION,
        ids.NAVIGATION,
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
        navigation=[Sensor(**nav) for nav in config[ids.NAVIGATION]],
        motion=[Sensor(**motion) for motion in config[ids.MOTION]],
        sounder=[Sensor(**sounder) for sounder in config[ids.SOUNDER]],
        waterline=[Waterline(**waterline) for waterline in config[ids.WATERLINE]],
        ssp_applied=[SoundSpeedProfile(**ssp) for ssp in config[ids.SSP_APPLIED]],
        attribute=[BDBattribute(**attr) for attr in config[ids.ATTRIBUTE]],
    )
