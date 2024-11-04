from dataclasses import dataclass


@dataclass(frozen=True)
class StationsError(Exception):
    message: str
    error: str
    status_code: int

    def __str__(self) -> str:
        return f"StationError: {self.message} - {self.error} (Status code: {self.status_code})"
