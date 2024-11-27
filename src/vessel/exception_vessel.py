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

    :param missing_keys: (list[str])
    """

    missing_keys: list[str]

    def __str__(self) -> str:
        return f"Certaines clés de configuration sont manquantes: {self.missing_keys}."


@dataclass(frozen=True)  #
class SensorNotFoundError(Exception):
    """
    Exception levée lorsqu'un capteur n'est pas trouvé.

    :param sensor_name: (str) Le nom du capteur.
    :param timestamp: (datetime) Le timestamp.
    """

    sensor_name: str
    timestamp: datetime

    def __str__(self) -> str:
        return f"Aucun capteur de type {self.sensor_name} trouvé pour le timestamp {self.timestamp}."


@dataclass(frozen=True)
class VesselConfigNotFoundError(Exception):
    """
    Exception levée lorsqu'une configuration de navire n'est pas trouvée.

    :param vessel_id: (str) L'identifiant du navire.
    """

    vessel_id: str

    def __str__(self) -> str:
        return f"La configuration du navire {self.vessel_id} n'existe pas."
