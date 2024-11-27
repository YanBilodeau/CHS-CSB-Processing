"""
Module contenant la classe abstraite VesselConfigManagerABC.

Ce module contient la classe abstraite VesselConfigManagerABC qui définit les méthodes pour gérer la configuration des navires.
"""

from abc import ABC, abstractmethod

from loguru import logger

from .vessel_config import VesselConfig

LOGGER = logger.bind(name="CSB-Pipeline.VesselConfigManager.ABC")


class VesselConfigManagerABC(ABC):
    """
    Classe abstraite définissant les méthodes pour gérer la configuration des navires.
    """
    def __init__(self, **kwargs):
        """
        Initialisation du gestionnaire de configuration des navires.

        :param kwargs: (dict) Clé - valeur.
        """
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

    @abstractmethod
    def add_veessel_config(self, vessel_config: VesselConfig) -> None:
        """
        Méthode permettant d'ajouter la configuration d'un navire.

        :param vessel_config: (VesselConfig) Configuration du navire.
        """
        pass

    @abstractmethod
    def update_vessel_config(self, vessel_id: str, vessel_config: VesselConfig) -> None:
        """
        Méthode permettant de mettre à jour la configuration d'un navire.

        :param vessel_id: (str) Identifiant du navire.
        :param vessel_config: (VesselConfig) Configuration du navire.
        """
        pass

    @abstractmethod
    def delete_vessel_config(self, vessel_id: str) -> None:
        """
        Méthode permettant de supprimer la configuration d'un navire.

        :param vessel_id: (str) Identifiant du navire.
        """
        pass

    @abstractmethod
    def commit_vessel_configs(self, **kwargs) -> None:
        """
        Méthode permettant de sauvegarder les configurations des navires.
        """
        pass
