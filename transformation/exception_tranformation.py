from dataclasses import dataclass


@dataclass(frozen=True)
class DataCleaningFunctionError(Exception):
    function: str

    def __str__(self):
        return f"La fonction de nettoyage '{self.function}' n'existe pas."
