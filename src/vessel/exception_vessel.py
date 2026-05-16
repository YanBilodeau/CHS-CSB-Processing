"""
Exceptions spécifiques à l'application Vessel.

Ce module contient les exceptions spécifiques à l'application Vessel.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import i18n


@dataclass(frozen=True)
class MissingConfigKeyError(Exception):
    """
    Exception levée lorsqu'une clé de configuration est manquante.

    :param missing_keys: Les clés manquantes.
    :type missing_keys: list[str]
    """

    missing_keys: list[str]
    """Les clés manquantes."""

    def __str__(self) -> str:
        return i18n.t(
            "vessel.exception_vessel.missing_config_key", missing_keys=self.missing_keys
        )


@dataclass(frozen=True)  #
class SensorNotFoundError(Exception):
    """
    Exception levée lorsqu'un capteur n'est pas trouvé.

    :param sensor_name: Le nom du capteur.
    :type sensor_name: str
    :param timestamp: Le timestamp.
    :type timestamp: datetime
    """

    sensor_name: str
    """Le type du capteur."""
    timestamp: datetime
    """Le timestamp."""

    def __str__(self) -> str:
        return i18n.t(
            "vessel.exception_vessel.sensor_not_found",
            sensor_name=self.sensor_name,
            timestamp=self.timestamp,
        )


@dataclass(frozen=True)
class VesselConfigNotFoundError(Exception):
    """
    Exception levée lorsqu'une configuration de navire n'est pas trouvée.

    :param vessel_id: L'identifiant du navire.
    :type vessel_id: str
    """

    vessel_id: str
    """L'identifiant du navire."""

    def __str__(self) -> str:
        return i18n.t(
            "vessel.exception_vessel.vessel_config_not_found", vessel_id=self.vessel_id
        )


@dataclass(frozen=True)
class VesselConfigManagerIdentifierError(Exception):
    """
    Exception levée lorsqu'une erreur survient lors de l'identification du gestionnaire de configuration de navires.

    :param manager_type: Le type de gestionnaire de navire.
    :type manager_type: str
    """

    manager_type: str
    """Le type de gestionnaire de navire."""

    def __str__(self) -> str:
        return i18n.t(
            "vessel.exception_vessel.manager_type_not_found",
            manager_type=self.manager_type,
        )


@dataclass(frozen=True)
class SensorConfigurationError(Exception):
    """
    Exception levée lorsque la configuration du capteur change durant la période de temps couverte par les données.
    """

    sensor_type: str
    """Le type de capteur."""

    def __str__(self) -> str:
        return i18n.t(
            "vessel.exception_vessel.sensor_config_changed",
            sensor_type=self.sensor_type,
        )


@dataclass(frozen=True)
class VesselConfigManagerError(Exception):
    """
    Exception levée lorsque la configuration du gestionnaire de navires est manquante
    pour récupérer la configuration du navire.

    :param vessel_id: L'identifiant du navire.
    :type vessel_id: str
    :param vessel_config_manager: La configuration du gestionnaire de navires.
    :type vessel_config_manager: Optional[VesselManagerConfig]
    """

    vessel_id: str
    """L'identifiant du navire."""
    vessel_config_manager: Optional[object]
    """La configuration du gestionnaire de navires."""

    def __str__(self) -> str:
        return i18n.t(
            "vessel.exception_vessel.manager_config_missing",
            vessel_config_manager=self.vessel_config_manager,
            vessel_id=self.vessel_id,
        )
