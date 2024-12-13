"""
Module de gestion de la factory de gestionnaire de configuration de navires.

Ce module contient la factory qui permet de récupérer la factory de gestionnaire de configuration
de navires en fonction du type.
"""

from enum import StrEnum

from loguru import logger

from .exception_vessel import VesselConfigManagerIdentifierError
from .vessel_config_manager_abc import VesselConfigManagerABC
from .vessel_config_json_manager import VesselConfigJsonManager
from .vessel_config_sqlite_manager import VesselConfigSQLiteManager

LOGGER = logger.bind(name="CSB-Processing.Vessel.ConfigManager.Factory")


class VesselConfigManagerType(StrEnum):
    """
    Enumération des types de gestionnaire de configuration de navires.
    """

    VesselConfigJsonManager = "VesselConfigJsonManager"
    """Gestionnaire de configuration de navires en JSON."""
    VesselConfigSQLiteManager = "VesselConfigSQLiteManager"
    """Gestionnaire de configuration de navires en SQLite."""


VESSEL_CONFIG_MANAGER_FACTORY: dict[
    VesselConfigManagerType, type[VesselConfigManagerABC]
] = {
    VesselConfigManagerType.VesselConfigJsonManager: VesselConfigJsonManager,
    VesselConfigManagerType.VesselConfigSQLiteManager: VesselConfigSQLiteManager,
}


def get_vessel_config_manager_factory(
    manager_type: VesselConfigManagerType,
) -> type[VesselConfigManagerABC]:
    """
    Récupère la factory du gestionnaire de navire en fonction du type.

    :param manager_type: Type de gestionnaire de navire.
    :type manager_type: VesselConfigManagerType
    :return: La factory du gestionnaire de navire.
    :rtype: type[VesselConfigManager]
    :raises VesselConfigManagerIdentifierError: Si le type de gestionnaire de navire n'est pas reconnu.
    """
    LOGGER.debug(
        f"Récupération de la factory du gestionnaire de navire pour le type '{manager_type}'."
    )

    if manager_type not in VESSEL_CONFIG_MANAGER_FACTORY:
        raise VesselConfigManagerIdentifierError(manager_type=manager_type)

    return VESSEL_CONFIG_MANAGER_FACTORY.get(manager_type)
