"""
Module de récupération de la configuration du navire.

Ce module permet de récupérer la configuration du navire.
"""

from functools import singledispatch

from loguru import logger

from .factory_vessel_config_manager import (
    get_vessel_config_manager_factory,
    VesselManagerProtocol,
)
from .vessel_config import VesselConfig
from .vessel_config_manager_abc import VesselConfigManagerABC


LOGGER = logger.bind(name="CSB-Processing.Vessel.VesselConfig.Factory")


@singledispatch
def get_vessel_config(
    vessel: str | VesselConfig,
    vessel_config_manager: VesselManagerProtocol,
    /,
) -> VesselConfig:
    """
    Récupère la configuration du navire.

    :param vessel: Identifiant du navire ou configuration du navire.
    :type vessel: str | VesselConfig
    :param vessel_config_manager: Gestionnaire de configuration du navire.
    :type vessel_config_manager: VesselManagerConfig
    :return: Configuration du navire.
    :rtype: VesselConfig
    """
    raise TypeError(
        f"Type non supporté pour la récupération de la configuration du navire : {type(vessel).__name__}."
    )


@get_vessel_config.register
def _(
    vessel: VesselConfig,
    vessel_config_manager_: VesselManagerProtocol,
) -> VesselConfig:
    """
    Récupère la configuration du navire.

    :param vessel: Configuration du navire.
    :type vessel: VesselConfig
    :return: Configuration du navire.
    :rtype: VesselConfig
    """
    LOGGER.debug(f"Configuration du navire : {vessel}.")

    return vessel


@get_vessel_config.register
def _(
    vessel: str,
    vessel_config_manager: VesselManagerProtocol,
) -> VesselConfig:
    """
    Récupère la configuration du navire.

    :param vessel: Identifiant du navire.
    :type vessel: str
    :param vessel_config_manager: Gestionnaire de configuration du navire.
    :type vessel_config_manager: VesselManagerConfig
    :return: Configuration du navire.
    :rtype: VesselConfig
    """
    vessel_config_manager: VesselConfigManagerABC = get_vessel_config_manager_factory(
        manager_type=vessel_config_manager.manager_type
    )(**vessel_config_manager.kwargs)

    vessel_config: VesselConfig = vessel_config_manager.get_vessel_config(
        vessel_id=vessel
    )

    LOGGER.debug(f"Configuration du navire : {vessel_config}.")

    return vessel_config
