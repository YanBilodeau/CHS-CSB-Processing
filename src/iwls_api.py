"""
Module pour l'initialisation et la gestion de l'API IWLS.

Ce module contient les fonctions pour initialiser l'API IWLS, récupérer l'environnement,
obtenir l'API et le gestionnaire des stations.
"""

from pathlib import Path
from typing import Optional

from loguru import logger

import config
import iwls_api_request as iwls
from tide import stations


LOGGER = logger.bind(name="CSB-Processing.IWLS-API")


def get_iwls_environment(iwls_config: config.IWLSAPIConfig) -> iwls.APIEnvironment:
    """
    Réccupère l'environnement de l'API IWLS à partir du fichier de configuration.

    :param iwls_config: Configuration de l'API IWLS.
    :type iwls_config: IWLSAPIConfig
    :return: Environnement de l'API IWLS.
    :rtype: APIEnvironment
    """
    activated_profile: iwls.EnvironmentType = iwls_config.profile.active
    activated_environment: iwls.APIEnvironment = iwls_config.__dict__.get(
        activated_profile
    )

    LOGGER.debug(
        f"Chargement du profil '{activated_profile}' pour l'API IWLS. [{activated_environment}]."
    )

    return activated_environment


def get_api(environment: iwls.APIEnvironment) -> stations.IWLSapiProtocol:
    """
    Récupère l'API IWLS à partir de l'environnement spécifié.

    :param environment: Environnement de l'API IWLS.
    :type environment: APIEnvironment
    :return: API IWLS.
    :rtype: IWLSapiProtocol
    """
    return iwls.get_iwls_api(  # type: ignore
        endpoint=environment.endpoint,
        handler_type=iwls.HandlerType.RATE_LIMITER,
        calls=environment.calls,
        period=environment.period,
    )


def get_stations_handler(
    endpoint_type: stations.EndpointTypeProtocol,
    api: stations.IWLSapiProtocol,
    ttl: int,
    cache_path: Path,
) -> stations.StationsHandlerABC:
    """
    Récupère le gestionnaire des stations.

    :param endpoint_type: Type de l'endpoint.
    :type endpoint_type: EndpointTypeProtocol
    :param api: API IWLS.
    :type api: IWLSapiProtocol
    :param ttl: Durée de vie du cache.
    :type ttl: int
    :param cache_path: Chemin du répertoire du cache.
    :type cache_path: Path
    :return: Gestionnaire des stations.
    :rtype: StationsHandlerABC
    """
    return stations.get_stations_factory(enpoint_type=endpoint_type)(
        api=api, ttl=ttl, cache_path=cache_path
    )


def initialize_iwls_api(
    config_path: Optional[Path] = None,
) -> tuple[config.IWLSAPIConfig, stations.StationsHandlerABC]:
    """
    Initialise l'API IWLS et retourne la configuration et le gestionnaire des stations.

    :param config_path: Chemin du fichier de configuration.
    :type config_path: Optional[Path]
    :return: Configuration IWLS et gestionnaire des stations.
    :rtype: tuple[config.IWLSAPIConfig, stations.StationsHandlerABC]
    """
    # Read the configuration file
    iwls_api_config: config.IWLSAPIConfig = config.get_api_config(
        config_file=config_path
    )
    # Get the environment of the API IWLS from the configuration file and the active profile
    api_environment: iwls.APIEnvironment = get_iwls_environment(
        iwls_config=iwls_api_config
    )
    # Get the API IWLS from the environment
    api: stations.IWLSapiProtocol = get_api(environment=api_environment)
    # Get the handler of the stations
    stations_handler: stations.StationsHandlerABC = get_stations_handler(
        api=api,
        endpoint_type=api_environment.endpoint.TYPE,
        ttl=iwls_api_config.cache.ttl,
        cache_path=iwls_api_config.cache.cache_path,
    )

    return iwls_api_config, stations_handler
