"""
Module pour la configuration du navire.

Ce module contient les classes et les fonctions pour la configuration du navire.
"""

from datetime import datetime
from enum import StrEnum

from loguru import logger
from pydantic import BaseModel

from .exception_vessel import MissingConfigKeyError, SensorNotFoundError
from . import vessel_ids as ids
from .vessel_models import VesselConfigDict


LOGGER = logger.bind(name="CSB-Pipeline.VesselConfig.BaseModel")


class AxisConvention(StrEnum):
    """
    Enumération des conventions d'axes.
    """

    CARIS: str = ids.CARIS
    """
    The X-Y-Z fields set the location from the Reference Point (0). The Reference Point is the point on
    the vessel where the X, Y, and Z axes intersect. The X, Y, and Z fields are defined as follows:
    - X: The athwart-ship distance of the sensor, positive to starboard.
    - Y: The along-ship distance of the sensor, positive to the bow.
    - Z: The vertical distance of the sensor, positive into the water.
    """


class Sensor(BaseModel):
    """
    Modèle de données pour un capteur.

    :param time_stamp: Date et heure.
    :type time_stamp: datetime
    :param x: Bras de levier X.
    :type x: float
    :param y: Bras de levier Y.
    :type y: float
    :param z: Bras de levier Z.
    :type z: float
    """

    time_stamp: datetime
    """Date et heure."""
    x: float
    """Bras de levier X."""
    y: float
    """Bras de levier Y."""
    z: float
    """Bras de levier Z."""


class BDBattribute(BaseModel):
    """
    Modèle de données pour un attribut BDB.

    :param time_stamp: Date et heure.
    :type time_stamp: datetime
    :param pltfrm: Plateforme.
    :type pltfrm: str
    :param sdghdw: Système de sondage.
    :type sdghdw: str
    :param poshdw: Système de positionnement.
    :type poshdw: str
    :param bureau: Bureau du fournisseur de données.
    :type bureau: str
    :param restrn: Restrictions de données.
    :type restrn: str
    """

    time_stamp: datetime
    """Date et heure."""
    pltfrm: str
    """Plateforme."""
    sdghdw: str
    """Système de sondage."""
    poshdw: str
    """Système de positionnement."""
    bureau: str
    """Bureau du fournisseur de données."""
    restrn: str
    """Restrictions de données."""


class Waterline(BaseModel):
    """
    Modèle de données pour une ligne d'eau.

    :param time_stamp: Date et heure.
    :type time_stamp: datetime
    :param z: Bras de levier Z.
    :type z: float
    """

    time_stamp: datetime
    """Date et heure."""
    z: float
    """Bras de levier Z."""


class SoundSpeedProfile(BaseModel):
    """
    Modèle de données pour un profil de vitesse du son.

    :param time_stamp: Date et heure.
    :type time_stamp: datetime
    :param ssp: True si le profil de vitesse du son est appliqué.
    :type ssp: bool
    """

    time_stamp: datetime
    """Date et heure."""
    ssp: bool
    """True si le profil de vitesse du son est appliqué."""


class VesselConfig(BaseModel):
    """
    Modèle de données pour la configuration du navire.

    :param id: Identifiant du navire.
    :type id: str
    :param axis_convention: Convention d'axes.
    :type axis_convention: AxisConvention
    :param navigation: Liste des données de navigation.
    :type navigation: list[Sensor]
    :param motion: Liste des données de mouvement.
    :type motion: list[Sensor]
    :param sounder: Liste des données du sondeur.
    :type sounder: list[Sensor]
    :param waterline: Liste des données de ligne d'eau.
    :type waterline: list[Waterline]
    :param ssp_applied: Liste des données de profil de vitesse du son appliqué.
    :type ssp_applied: list[SoundSpeedProfile]
    :param attribute: Liste des données d'attribut.
    :type attribute: list[BDBattribute]
    """

    id: str
    """Identifiant du navire."""
    axis_convention: AxisConvention
    """Convention des axes."""
    navigation: list[Sensor]
    """Données des bras de levier du capteur de navigation."""
    motion: list[Sensor]
    """Données des bras de levier du capteur de mouvement."""
    sounder: list[Sensor]
    """Données des bras de levier du sondeur."""
    waterline: list[Waterline]
    """Données des bras de levier de la ligne d'eau."""
    ssp_applied: list[SoundSpeedProfile]
    """Données de profil de vitesse du son appliqué."""
    attribute: list[BDBattribute]
    """Données des attributs BDB."""

    def get_sensor(
        self, sensor_name: str, timestamp: datetime
    ) -> Sensor | Waterline | SoundSpeedProfile | BDBattribute:
        """
        Récupère les données d'un type de capteur à un instant donné.

        :param sensor_name: Nom du capteur.
        :type sensor_name: str
        :param timestamp: Une date et heure.
        :type timestamp: datetime
        :return: Données du capteur pour le moment donné.
        :rtype: Sensor | Waterline | SoundSpeedProfile | BDBattribute
        :raises SensorNotFoundError: Si le capteur n'existe pas.
        """
        LOGGER.debug(
            f"Récupération des données du capteur {sensor_name} pour {timestamp}."
        )

        sensors: list[Sensor | Waterline | SoundSpeedProfile | BDBattribute] = getattr(
            self, sensor_name
        )

        closest_sensor: Sensor | Waterline | SoundSpeedProfile | BDBattribute | None = (
            min(
                (sensor for sensor in sensors if timestamp >= sensor.time_stamp),
                key=lambda sensor: timestamp - sensor.time_stamp,
                default=None,
            )
        )

        if closest_sensor is None:
            raise SensorNotFoundError(sensor_name=sensor_name, timestamp=timestamp)

        return closest_sensor

    def get_navigation(self, timestamp: datetime) -> Sensor:
        """
        Méthode pour récupérer les données de navigation à un instant donné.

        :param timestamp: Une date et heure.
        :type timestamp: datetime
        :return: Données de navigation pour le moment donné.
        :rtype: Sensor
        """
        return self.get_sensor(sensor_name=ids.NAVIGATION, timestamp=timestamp)

    def get_motion(self, timestamp: datetime) -> Sensor:
        """
        Méthode pour récupérer les données de mouvement à un instant donné.

        :param timestamp: Une date et heure.
        :type timestamp: datetime
        :return: Données de mouvement pour le moment donné.
        :rtype: Sensor
        """
        return self.get_sensor(sensor_name=ids.MOTION, timestamp=timestamp)

    def get_sounder(self, timestamp: datetime) -> Sensor:
        """
        Méthode pour récupérer les données du sondeur à un instant donné.

        :param timestamp: Une date et heure.
        :type timestamp: datetime
        :return: Données du sondeur pour le moment donné.
        :rtype: Sensor
        """
        return self.get_sensor(sensor_name=ids.SOUNDER, timestamp=timestamp)

    def get_waterline(self, timestamp: datetime) -> Waterline:
        """
        Méthode pour récupérer les données de ligne d'eau à un instant donné.

        :param timestamp: Une date et heure.
        :type timestamp: datetime
        :return: Données de ligne d'eau pour le moment donné.
        :rtype: Waterline
        """
        return self.get_sensor(sensor_name=ids.WATERLINE, timestamp=timestamp)

    def get_ssp_applied(self, timestamp: datetime) -> SoundSpeedProfile:
        """
        Méthode pour récupérer les données de profil de vitesse du son appliqué à un instant donné.

        :param timestamp: Une date et heure.
        :type timestamp: datetime
        :return: Données de profil de vitesse du son appliqué pour le moment donné.
        :rtype: SoundSpeedProfile
        """
        return self.get_sensor(sensor_name=ids.SSP_APPLIED, timestamp=timestamp)

    def get_attribute(self, timestamp: datetime) -> BDBattribute:
        """
        Méthode pour récupérer les données d'attribut à un instant donné.

        :param timestamp: Une date et heure.
        :type timestamp: datetime
        :return: Données d'attribut pour le moment donné.
        :rtype: BDBattribute
        """
        return self.get_sensor(sensor_name=ids.ATTRIBUTE, timestamp=timestamp)


def get_vessel_config_from_config_dict(config: VesselConfigDict) -> VesselConfig:
    """
    Récupère la configuration du navire.

    :param config: Configuration du navire.
    :type config: VesselConfigDict
    :return: Configuration du navire.
    :rtype: VesselConfig
    :raises MissingConfigKeyError: Si des clés de configuration sont manquantes.
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
