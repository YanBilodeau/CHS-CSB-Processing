from pathlib import Path
from typing import Optional

from loguru import logger
import toml


LOGGER = logger.bind(name="CSB-Pipeline.Config.LoadConfig")


def load_config(config_file: Optional[Path]) -> dict:
    """
    Retournes les données de configuration du fichier TOML.

    :param config_file: Le chemin du fichier de configuration.
    :type config_file: Optional[Path]
    :return: Les données de configuration.
    :rtype: DataConfigDict
    """
    LOGGER.debug(f"Chargement du fichier de configuration : '{config_file}'.")

    with open(config_file, "r") as file:
        data = toml.load(file)

    return data
