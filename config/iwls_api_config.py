import re
from pathlib import Path
from typing import Optional

from loguru import logger
from pydantic import BaseModel, field_validator

from iwls_api_request import TimeSeries
from iwls_api_request.api_config import (
    APIEnvironment,
    APIProfile,
    EnvironmentDict,
    ProfileDict,
    load_config,
    get_environment_config,
)

LOGGER = logger.bind(name="CSB-Pipeline.Config.IWLSAPIConfig")

CONFIG_FILE: Path = Path(__file__).parent.parent / "iwls_API_config.toml"

TimeSeriesDict = dict[str, list[str]]
IWLSapiDict = dict[str, dict[str, TimeSeriesDict | EnvironmentDict | ProfileDict]]


class TimeSeriesPriority(BaseModel):
    priority: list[TimeSeries]
    max_time_gap: str | None
    threeshold_interpolation_filling: str | None

    @field_validator("max_time_gap", "threeshold_interpolation_filling")
    def validate_time_gap(cls, value):
        if value == "":
            return None

        if value is not None:
            pattern = re.compile(r"^\d+\s*(minutes|hours)$")
            if not pattern.match(value):
                raise ValueError(
                    'Le time gap doit être au format "<number> <minutes|hours>".'
                )

        return value


class IWLSAPIConfig(BaseModel):
    dev: Optional[APIEnvironment]
    prod: Optional[APIEnvironment]
    public: Optional[APIEnvironment]
    time_series: TimeSeriesPriority
    profile: APIProfile


def get_api_config(config_file: Optional[Path] = CONFIG_FILE) -> IWLSAPIConfig:
    """
    Retournes la configuration de l'API IWLS

    :param config_file: Le fichier de configuration.
    :type config_file: Path
    :return: Un objet APIConfig.
    :rtype: APIConfig
    """
    config_data: IWLSapiDict = load_config(config_file=config_file)
    environments: EnvironmentDict = get_environment_config(
        config_data["IWLS"]["API"]["ENVIRONMENT"]
    )
    LOGGER.debug(f"Initialisation de la configuration de l'API IWLS.")

    return IWLSAPIConfig(
        dev=environments["dev"] if "dev" in environments else None,
        prod=environments["prod"] if "prod" in environments else None,
        public=environments["public"] if "public" in environments else None,
        time_series=TimeSeriesPriority(
            priority=config_data["IWLS"]["API"]["TimeSeries"]["priority"],
            max_time_gap=config_data["IWLS"]["API"]["TimeSeries"].get("max_time_gap"),
            threeshold_interpolation_filling=config_data["IWLS"]["API"][
                "TimeSeries"
            ].get("threeshold_interpolation-filling"),
        ),
        profile=APIProfile(**config_data["IWLS"]["API"]["PROFILE"]),
    )