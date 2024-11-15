from dataclasses import dataclass
from pathlib import Path

from . import parser_ids as ids


@dataclass(frozen=True)
class LowranceError(Exception):
    file: Path


@dataclass(frozen=True)
class LowranceDataframeTimeError(LowranceError):
    def __str__(self) -> str:
        return f"Erreur lors de la lecture du fichier : {self.file}. Le fichier n'a pas de colonne '{ids.TIME_LOWRANCE}'."


@dataclass(frozen=True)
class LowranceDataframeDepthError(LowranceError):
    def __str__(self) -> str:
        return f"Erreur lors de la lecture du fichier : {self.file}. Le fichier n'a pas de colonne '{ids.DEPTH_LOWRANCE}'."


@dataclass(frozen=True)
class LowranceDataframeLongitudeError(LowranceError):
    def __str__(self) -> str:
        return f"Erreur lors de la lecture du fichier : {self.file}. Le fichier n'a pas de colonne '{ids.LONGITUDE_LOWRANCE}'."


@dataclass(frozen=True)
class LowranceDataframeLatitudeError(LowranceError):
    def __str__(self) -> str:
        return f"Erreur lors de la lecture du fichier : {self.file}. Le fichier n'a pas de colonne '{ids.LATITUDE_LOWRANCE}'."
