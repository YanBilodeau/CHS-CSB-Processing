from dataclasses import dataclass


@dataclass
class MissingConfigKeyError(Exception):
    missing_keys: list[str]

    def __str__(self) -> str:
        return f"Certaines clés de configuration sont manquantes: {self.missing_keys}."