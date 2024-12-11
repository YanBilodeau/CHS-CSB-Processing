"""
Module permettant de gérer la configuration des navires à partir d'un fichier JSON.

Ce module contient la classe VesselConfigJsonManager qui permet de gérer la configuration des navires à partir d'un fichier JSON.
"""

from datetime import datetime
import json
from pathlib import Path

from loguru import logger

from .exception_vessel import VesselConfigNotFoundError
from .vessel_config_manager_abc import VesselConfigManagerABC
from .vessel_config import (
    VesselConfig,
    get_vessel_config_from_config_dict,
    VesselConfigDict,
)
from . import vessel_ids as ids

LOGGER = logger.bind(name="CSB-Pipeline.VesselConfigManager.JSON")


class VesselConfigJsonManager(VesselConfigManagerABC):
    """
    Classe permettant de gérer la configuration des navires à partir d'un fichier JSON.
    """

    def __init__(self, json_config_path: Path | str):
        """
        Initialisation du gestionnaire de configuration des navires à partir d'un fichier JSON.

        :param json_config_path: Chemin du fichier JSON.
        :type json_config_path: Path | str
        """
        super().__init__()
        self._vessel_configs = self._load_vessel_configs_file(
            json_config_path=json_config_path
        )

    @staticmethod
    def _load_vessel_configs_file(json_config_path: Path) -> dict[str, VesselConfig]:
        """
        Méthode permettant de charger la configuration des navires depuis un fichier JSON.

        :param json_config_path: Chemin du fichier JSON.
        :type json_config_path: Path
        :return: Les configurations des navires.
        :type: dict[str, VesselConfigDict]
        :return: Configurations des navires.
        :rtype: dict[str, VesselConfig]
        :raises FileNotFoundError: Si le fichier de configuration des navires n'existe pas.
        """
        json_config_path: Path = Path(json_config_path)

        LOGGER.debug(
            f"Chargement du fichier de configuration des navires : {json_config_path}."
        )

        if not json_config_path.exists():
            raise FileNotFoundError(
                f"Le fichier de configuration des navires n'existe pas: {json_config_path}."
            )

        with open(json_config_path, "r") as file:
            vessel_configs: list[VesselConfigDict] = json.load(file)

        return {
            vessel[ids.ID]: get_vessel_config_from_config_dict(vessel)
            for vessel in vessel_configs
        }

    def commit_vessel_configs(self, json_config_path: Path) -> None:
        """
        Méthode permettant de sauvegarder la configuration des navires dans un fichier JSON.

        :param json_config_path: Chemin du fichier JSON.
        :type json_config_path: Path
        :raises TypeError: Si un objet n'est pas sérialisable.
        """

        def default_serializer(object_):
            if isinstance(object_, datetime):
                return object_.strftime("%Y-%m-%dT%H:%M:%SZ")

            raise TypeError(
                f"Les objets de type {object_.__class__.__name__} ne sont pas sérialisables."
            )

        LOGGER.debug(
            f"Sauvegarde du fichier de configuration des navires : {json_config_path}."
        )

        with open(json_config_path, "w") as file:
            json.dump(
                [config.model_dump() for config in self._vessel_configs.values()],
                file,  # type: ignore
                indent=2,
                default=default_serializer,
            )

    def get_vessel_config(self, vessel_id: str) -> VesselConfig:
        """
        Méthode permettant de récupérer la configuration d'un navire.

        :param vessel_id: Identifiant du navire.
        :type vessel_id: str
        :return: Configuration du navire.
        :rtype: VesselConfig
        :raises VesselConfigNotFoundError: Si la configuration du navire n'existe pas.
        """
        LOGGER.debug(f"Récupération de la configuration du navire : {vessel_id}.")

        if vessel_id not in self._vessel_configs:
            raise VesselConfigNotFoundError(vessel_id=vessel_id)

        return self._vessel_configs[vessel_id]

    def get_vessel_configs(self) -> list[VesselConfig]:
        """
        Méthode permettant de récupérer la configuration de tous les navires.

        :return: Configurations des navires.
        :rtype: list[VesselConfig]
        """
        LOGGER.debug("Récupération de la configuration de tous les navires.")

        return [config for config in self._vessel_configs.values()]

    def add_veessel_config(self, vessel_config: VesselConfig) -> None:
        """
        Méthode permettant d'ajouter la configuration d'un navire.

        :param vessel_config: Configuration du navire.
        :type vessel_config: VesselConfig
        """
        LOGGER.debug(f"Ajout de la configuration du navire : {vessel_config.id}.")

        self._vessel_configs[vessel_config.id] = vessel_config

    def update_vessel_config(self, vessel_id: str, vessel_config: VesselConfig) -> None:
        """
        Méthode permettant de mettre à jour la configuration d'un navire.

        :param vessel_id: Identifiant du navire.
        :type vessel_id: str
        :param vessel_config: Configuration du navire.
        :type vessel_config: VesselConfig
        """
        LOGGER.debug(f"Mise à jour de la configuration du navire : {vessel_id}.")

        self._vessel_configs[vessel_id] = vessel_config

    def delete_vessel_config(self, vessel_id: str) -> None:
        """
        Méthode permettant de supprimer la configuration d'un navire.

        :param vessel_id: Identifiant du navire.
        :type vessel_id: str
        """
        LOGGER.debug(f"Suppression de la configuration du navire : {vessel_id}.")

        del self._vessel_configs[vessel_id]
