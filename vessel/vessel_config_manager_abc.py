from abc import ABC, abstractmethod

from .vessel_config import VesselConfig


class VesselConfigManagerABC(ABC):
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
