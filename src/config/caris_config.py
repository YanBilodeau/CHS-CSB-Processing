"""
Module de configuration pour l'API Python de Caris.

Ce module contient la classe de configuration pour l'API Python de Caris.
"""

from pathlib import Path

from loguru import logger
from pydantic import BaseModel, Field

from config.helper import load_config

LOGGER = logger.bind(name="CSB-Processing.Caris.Config")

ConfigDict = dict[str, str | float]


class CarisAPIConfig(BaseModel):
    """
    Classe de configuration pour l'API Python de Caris.

    :param base_path: Le chemin de base de l'API Python de Caris.
    :type base_path: str
    :param software: Le logiciel de Caris.
    :type software: str
    :param version: La version du logiciel de Caris.
    :type version: str
    :param python_version: La version de Python.
    :type python_version: str
    :param python_path: Le chemin de l'API Python de Caris.
    :type python_path: Path
    :raises ValueError: Si l'API Python de Caris n'existe pas à l'emplacement spécifié.
    """

    base_path: str
    software: str
    version: str
    python_version: str
    python_path: Path = Field(default=None)

    def __init__(self, **values) -> None:
        super().__init__(**values)
        self.python_path = (
            Path(self.base_path)
            / self.software
            / self.version
            / "python"
            / self.python_version
        )

        if not self.python_path.exists():
            raise ValueError(
                f"L'API Python de Caris n'existe pas à l'emplacement {self.python_path}."
            )


def get_caris_api_config(
    config_file: Path,
) -> CarisAPIConfig:
    """
    Retournes la configuration pour l'API Python de Caris.

    :param config_file: Le chemin du fichier de configuration.
    :type config_file: Path
    :return: La configuration pour l'API Python de Caris.
    :rtype: CarisAPIConfig
    """
    config_dict = load_config(config_file=config_file)

    config_caris_api: ConfigDict = (
        config_dict.get("CARIS").get("Environment") if "CARIS" in config_dict else None
    )
    if not config_caris_api:
        raise ValueError(
            f"Aucune configuration pour l'API de Caris n'a été trouvée dans le fichier de configuration : {config_file}."
        )

    LOGGER.debug(f"Initialisation de la configuration pour l'API de Caris.")

    return CarisAPIConfig(**config_caris_api)
