from dataclasses import dataclass
from pathlib import Path
from typing import Type


@dataclass(frozen=True)
class ParsingError(Exception):
    file: Path
    column: str

    def __str__(self) -> str:
        return f"Erreur lors de la lecture du fichier : {self.file}. Le fichier n'a pas de colonne '{self.column}'."


@dataclass(frozen=True)
class ParsingDataframeTimeError(ParsingError):
    pass


@dataclass(frozen=True)
class ParsingDataframeDepthError(ParsingError):
    pass


@dataclass(frozen=True)
class ParsingDataframeLongitudeError(ParsingError):
    pass


@dataclass(frozen=True)
class ParsingDataframeLatitudeError(ParsingError):
    pass


ColumnExceptions = list[tuple[str, Type[ParsingError]]]
