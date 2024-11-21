from abc import ABC, abstractmethod

from loguru import logger

from .vessel_config import VesselConfig

LOGGER = logger.bind(name="CSB-Pipeline.VesselConfigManager.ABC")


class VesselConfigManagerABC(ABC):
    def __init__(self, **kwargs):
        LOGGER.debug(
            f"Initialisation du gestionnaire de configuration des navires : {self.__class__.__name__}."
        )

    @abstractmethod
    def get_vessel_config(self, vessel_id: str) -> VesselConfig:
        """
        Méthode permettant de récupérer la configuration d'un navire.

        :param vessel_id: (str) Identifiant du navire.
        :return: (VesselConfig) Configuration du navire.
        """
        pass

    @abstractmethod
    def get_vessel_configs(self) -> list[VesselConfig]:
        """
        Méthode permettant de récupérer la configuration de tous les navires.

        :return: (list[VesselConfig]) Configurations des navires.
        """
        pass
