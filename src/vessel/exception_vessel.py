"""
Exceptions spécifiques à l'application Vessel.

Ce module contient les exceptions spécifiques à l'application Vessel.
"""

from dataclasses import dataclass
from datetime import datetime


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
        return f"Certaines clés de configuration sont manquantes: {self.missing_keys}."


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
        return f"Aucun capteur de type {self.sensor_name} trouvé pour le timestamp {self.timestamp}."


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
        return f"La configuration du navire {self.vessel_id} n'existe pas."


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
        return f"Le type de gestionnaire de navire '{self.manager_type}' n'existe pas."


@dataclass(frozen=True)
class SensorConfigurationError(Exception):
    """
    Exception levée lorsque la configuration du capteur change durant la période de temps couverte par les données.
    """

    sensor_type: str
    """Le type de capteur."""

    def __str__(self) -> str:
        return f"La configuration du capteur {self.sensor_type} a changé durant la période de temps couverte par les données."
