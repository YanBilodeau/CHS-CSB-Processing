import re
from datetime import timedelta
from pathlib import Path
from typing import Optional

from loguru import logger
from pydantic import BaseModel, field_validator

import iwls_api_request as iwls

LOGGER = logger.bind(name="CSB-Pipeline.Config.IWLSAPIConfig")

CONFIG_FILE: Path = Path(__file__).parent.parent / "CONFIG_iwls_API.toml"

TimeSeriesDict = dict[str, list[str]]
IWLSapiDict = dict[
    str, dict[str, TimeSeriesDict | iwls.EnvironmentDict | iwls.ProfileDict]
]


class TimeSeriesConfig(BaseModel):
    priority: list[iwls.TimeSeries]
    max_time_gap: str | None
    threshold_interpolation_filling: str | None
    wlo_qc_flag_filter: list[str] | None
    buffer_time: timedelta | None

    def __init__(self, **data):
        super().__init__(**data)
        if isinstance(data.get("buffer_time"), int):
            self.buffer_time = timedelta(hours=data["buffer_time"])

    @field_validator("max_time_gap", "threshold_interpolation_filling")
    def validate_time_gap(cls, value):
        if value == "":
            return None

        if value is not None:
            pattern = re.compile(r"^\d+\s*(min|h)$")
            if not pattern.match(value):
                raise ValueError(
                    'Le time gap doit être au format "<number> <minutes|hours>".'
                )

        return value


class IWLSAPIConfig(BaseModel):
    dev: Optional[iwls.APIEnvironment]
    prod: Optional[iwls.APIEnvironment]
    public: Optional[iwls.APIEnvironment]
    time_series: TimeSeriesConfig
    profile: iwls.APIProfile


def get_api_config(config_file: Optional[Path] = CONFIG_FILE) -> IWLSAPIConfig:
    """
    Retournes la configuration de l'API IWLS

    :param config_file: Le fichier de configuration.
    :type config_file: Path
    :return: Un objet APIConfig.
    :rtype: APIConfig
    """
    config_data: IWLSapiDict = iwls.load_config(config_file=config_file)
    environments: iwls.EnvironmentDict = iwls.get_environment_config(
        config_data["IWLS"]["API"]["ENVIRONMENT"]
    )
    LOGGER.debug(f"Initialisation de la configuration de l'API IWLS.")

    return IWLSAPIConfig(
        dev=environments["dev"] if "dev" in environments else None,
        prod=environments["prod"] if "prod" in environments else None,
        public=environments["public"] if "public" in environments else None,
        time_series=TimeSeriesConfig(
            priority=config_data["IWLS"]["API"]["TimeSeries"]["priority"],
            max_time_gap=config_data["IWLS"]["API"]["TimeSeries"].get("max_time_gap"),
            threshold_interpolation_filling=config_data["IWLS"]["API"][
                "TimeSeries"
            ].get("threshold_interpolation-filling"),
            wlo_qc_flag_filter=config_data["IWLS"]["API"]["TimeSeries"].get(
                "wlo_qc_flag_filter"
            ),
            buffer_time=config_data["IWLS"]["API"]["TimeSeries"].get("buffer_time"),
        ),
        profile=iwls.APIProfile(**config_data["IWLS"]["API"]["PROFILE"]),
    )
