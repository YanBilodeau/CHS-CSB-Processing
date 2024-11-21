import json
from pathlib import Path

from loguru import logger

from .vessel_config_manager_abc import VesselConfigManagerABC
from .vessel_config import (
    VesselConfig,
    get_vessel_config_from_config_dict,
    VesselConfigDict,
)
from . import vessel_ids as ids

LOGGER = logger.bind(name="CSB-Pipeline.VesselConfigManager.JSON")


class VesselConfigJsonManager(VesselConfigManagerABC):
    def __init__(self, json_config_path: Path):
        super().__init__()
        self._vessel_configs = self._load_vessel_configs_file(
            json_config_path=json_config_path
        )

    @staticmethod
    def _load_vessel_configs_file(json_config_path: Path) -> dict[str, VesselConfig]:
        """
        Méthode permettant de charger la configuration des navires depuis un fichier JSON.

        :param json_config_path: (Path) Chemin du fichier JSON.
        :return: (dict[str, VesselConfigDict]) Les configurations des navires.
        :raises FileNotFoundError: Si le fichier de configuration des navires n'existe pas.
        """
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

    def get_vessel_config(self, vessel_id: str) -> VesselConfig:
        """
        Méthode permettant de récupérer la configuration d'un navire.

        :param vessel_id: (str) Identifiant du navire.
        :return: (VesselConfig) Configuration du navire.
        :raises ValueError: Si la configuration du navire n'existe pas.
        """
        LOGGER.debug(f"Récupération de la configuration du navire : {vessel_id}.")

        if vessel_id not in self._vessel_configs:
            raise ValueError(f"La configuration du navire {vessel_id} n'existe pas.")

        return self._vessel_configs[vessel_id]

    def get_vessel_configs(self) -> list[VesselConfig]:
        """
        Méthode permettant de récupérer la configuration de tous les navires.

        :return: (list[VesselConfig]) Configurations des navires.
        """
        LOGGER.debug("Récupération de la configuration de tous les navires.")

        return [config for config in self._vessel_configs.values()]
