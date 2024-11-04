from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Optional, Collection


@dataclass(frozen=True)
class CachedSessionConfig:
    db: Optional[Path] = field(default=Path(__file__).resolve().parent / ".cache/IWLS")
    backend: Optional[str] = field(default="sqlite")
    allowable_methods: Optional[tuple[str]] = field(default=("GET",))
    expire_after: Optional[int] = field(default=600)
    timeout: Optional[int] = field(default=5)


@dataclass
class RetryAdapterConfig:
    max_retry: Optional[int] = 5
    backoff_factor: Optional[int] = 2
    status_code: Optional[Collection[int]] = field(default=(429, 500, 502, 503, 504))


@dataclass
class Rate:
    calls: int = 100
    period: int = 1


@dataclass
class Response:
    status_code: int = 200
    data: dict | list | str = None
    message: str = None
    error: str | list = None

    @property
    def is_ok(self) -> bool:
        return self.status_code == 200


class ResponseType(StrEnum):
    JSON: str = "json"
    TEXT: str = "text"


class SessionType(StrEnum):
    REQUESTS: str = "requests"
    CACHE: str = "cache"
