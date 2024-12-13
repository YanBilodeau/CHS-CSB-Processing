"""
Module contenant la classe abstraite VesselConfigManagerABC.

Ce module contient la classe abstraite VesselConfigManagerABC qui définit les méthodes pour gérer la configuration des navires.
"""

from abc import ABC, abstractmethod
from typing import Any

from loguru import logger

from .vessel_config import VesselConfig

LOGGER = logger.bind(name="CSB-Processing.VesselConfigManager.ABC")


class VesselConfigManagerABC(ABC):
    """
    Classe abstraite définissant les méthodes pour gérer la configuration des navires.
    """

    def __init__(self, **kwargs: Any):
        """
        Initialisation du gestionnaire de configuration des navires.

        :param kwargs: Dictionnaire des paramètres.
        :type kwargs: dict
        """
        LOGGER.debug(
            f"Initialisation du gestionnaire de configuration des navires : {self.__class__.__name__}."
        )

    @abstractmethod
    def get_vessel_config(self, vessel_id: str) -> VesselConfig:
        """
        Méthode permettant de récupérer la configuration d'un navire.

        :param vessel_id: Identifiant du navire.
        :type vessel_id: str
        :return: Configuration du navire.
        :rtype: VesselConfig
        """
        pass

    @abstractmethod
    def get_vessel_configs(self) -> list[VesselConfig]:
        """
        Méthode permettant de récupérer la configuration de tous les navires.

        :return: Configurations des navires.
        :rtype: list[VesselConfig]
        """
        pass

    @abstractmethod
    def add_veessel_config(self, vessel_config: VesselConfig) -> None:
        """
        Méthode permettant d'ajouter la configuration d'un navire.

        :param vessel_config: Configuration du navire.
        :type vessel_config: VesselConfig
        """
        pass

    @abstractmethod
    def update_vessel_config(self, vessel_id: str, vessel_config: VesselConfig) -> None:
        """
        Méthode permettant de mettre à jour la configuration d'un navire.

        :param vessel_id: Identifiant du navire.
        :type vessel_id: str
        :param vessel_config: Configuration du navire.
        :type vessel_config: Vessel
        """
        pass

    @abstractmethod
    def delete_vessel_config(self, vessel_id: str) -> None:
        """
        Méthode permettant de supprimer la configuration d'un navire.

        :param vessel_id: Identifiant du navire.
        :type vessel_id: str
        """
        pass

    @abstractmethod
    def commit_vessel_configs(self, **kwargs) -> None:
        """
        Méthode permettant de sauvegarder les configurations des navires.

        :param kwargs: Dictionnaire des paramètres.
        :type kwargs: dict
        """
        pass
