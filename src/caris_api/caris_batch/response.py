from dataclasses import dataclass, field
from enum import Enum

from . import ids_batch as ids


class StatusCode(Enum):
    OK = 0
    ERROR = -1


@dataclass(frozen=True)
class CarisBatchResponse:
    stdout: list[str]
    stderr: list[str]
    status_code: StatusCode = field(init=False)
    # output_path: Path = field(default=None)

    def __post_init__(self):
        object.__setattr__(
            self,
            ids.STATUS_CODE,
            StatusCode.OK if not self.stderr else StatusCode.ERROR,
        )

    @property
    def is_ok(self) -> bool:
        """
        Méthode retournant True si le SatusCode est OK, False sinon.
        """
        return True if self.status_code == StatusCode.OK else False

    @property
    def stdout_message(self) -> str:
        """
        Méthode retournant le message de sortie.
        """
        return "\n".join(self.stdout)

    @property
    def stderr_message(self) -> str:
        """
        Méthode retournant le message d'erreur.
        """
        return "\n".join(self.stderr)

    def __str__(self) -> str:
        """
        Surchage de l'opérateur __str__.

        :return: (str) Une représentation de l'instance de HipsCommandLineUtilitiesResponse.
        """
        return "\n".join(self.stdout) + "\n".join(self.stderr)
