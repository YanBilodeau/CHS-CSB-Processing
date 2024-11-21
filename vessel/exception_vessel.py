from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class MissingConfigKeyError(Exception):
    missing_keys: list[str]

    def __str__(self) -> str:
        return f"Certaines clés de configuration sont manquantes: {self.missing_keys}."


@dataclass(frozen=True)  #
class SensorNotFoundError(Exception):
    sensor_name: str
    timestamp: datetime

    def __str__(self) -> str:
        return f"Aucun capteur de type {self.sensor_name} trouvé pour le timestamp {self.timestamp}."
