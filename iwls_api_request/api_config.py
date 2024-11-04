from pathlib import Path
from typing import Optional

import toml
from loguru import logger
from pydantic import BaseModel, field_validator

from .api import (
    Endpoint,
    EndpointPrivateProd,
    EndpointPrivateDev,
    EndpointPublic,
    EndpointType,
)
from .api_facade import EnvironmentType

LOGGER = logger.bind(name="IWLS.Config.IWLSAPIConfig")

CONFIG_FILE: Path = Path(__file__).parent.parent.parent / "config" / "config_API.toml"

ENDPOINTS_FACTORY: dict[EndpointType, type[Endpoint]] = {
    EndpointType.PRIVATE_PROD: EndpointPrivateProd,
    EndpointType.PRIVATE_DEV: EndpointPrivateDev,
    EndpointType.PUBLIC: EndpointPublic,
}

EnvironmentDict = dict[str, dict[str, str | int]]
ProfileDict = dict[str, str]
IWLSapiDict = dict[str, dict[str, EnvironmentDict | ProfileDict]]


class APIEnvironment(BaseModel):
    name: str
    endpoint: Endpoint
    calls: int
    period: int

    class Config:
        arbitrary_types_allowed = True

    @field_validator("calls", "period")
    def must_be_positive(cls, value):
        if value <= 0:
            raise ValueError(
                "La valeur doit être positive pour l'attribut calls et period."
            )

        return value


class APIProfile(BaseModel):
    active: EnvironmentType


class IWLSAPIConfig(BaseModel):
    dev: APIEnvironment
    prod: APIEnvironment
    profile: APIProfile


def load_config(config_file: Optional[Path] = CONFIG_FILE) -> IWLSapiDict:
    """
    Retournes la configuration de l'API IWLS

    :param config_file: Le fichier de configuration.
    :type config_file: Path
    :return: La configuration de l'API IWLS.
    :rtype: IWLSapiDict
    """
    LOGGER.debug(f"Chargement du fichier de configuration : '{config_file}'.")

    with open(config_file, "r") as file:
        data = toml.load(file)

    return data


def get_environment_config(
    api_config_dict: EnvironmentDict,
) -> dict[str, APIEnvironment]:
    """
    Retournes les configurations des environnements de l'API IWLS

    :param api_config_dict: La configuration de l'API IWLS.
    :type api_config_dict: IWLSapiDict
    :return: Les configurations des environnements de l'API IWLS.
    :rtype: dict[str, APIEnvironment]
    """
    LOGGER.debug(f"Initialisation des configurations des environnements de l'API IWLS.")

    return {
        env: APIEnvironment(
            name=api_config_dict[env]["name"],
            endpoint=ENDPOINTS_FACTORY.get(
                EndpointType.from_str(api_config_dict[env]["endpoint"])
            )(),
            calls=api_config_dict[env]["calls"],
            period=api_config_dict[env]["period"],
        )
        for env in api_config_dict
    }


def get_api_config(config_file: Optional[Path] = CONFIG_FILE) -> IWLSAPIConfig:
    """
    Retournes la configuration de l'API IWLS

    :param config_file: Le fichier de configuration.
    :type config_file: Path
    :return: Un objet APIConfig.
    :rtype: IWLSAPIConfig
    """

    api_config: IWLSapiDict = load_config(config_file=config_file)
    environments: dict[str, APIEnvironment] = get_environment_config(
        api_config_dict=api_config["ENVIRONMENT"]
    )
    LOGGER.debug(f"Initialisation de la configuration de l'API IWLS.")

    return IWLSAPIConfig(
        dev=environments["dev"],
        prod=environments["prod"],
        profile=APIProfile(**api_config["PROFILE"]),
    )
