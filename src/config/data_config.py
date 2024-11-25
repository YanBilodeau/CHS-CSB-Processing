from pathlib import Path
from pydantic import BaseModel, field_validator
from typing import Optional

from loguru import logger
import toml


LOGGER = logger.bind(name="CSB-Pipeline.Config.DataConfig")

CONFIG_FILE: Path = Path(__file__).parent.parent / "CONFIG_data_transformation.toml"

DataFilterDict = dict[str, int | float]
DataConfigDict = dict[str, dict[str, dict[str, DataFilterDict]]]

MIN_LATITUDE: int | float = -90
MAX_LATITUDE: int | float = 90
MIN_LONGITUDE: int | float = -180
MAX_LONGITUDE: int | float = 180
MIN_DEPTH: int | float = 0
MAX_DEPTH: int | float | None = None


class DataFilterConfig(BaseModel):
    min_latitude: int | float = MIN_LATITUDE
    max_latitude: int | float = MAX_LATITUDE
    min_longitude: int | float = MIN_LONGITUDE
    max_longitude: int | float = MAX_LONGITUDE
    min_depth: int | float = MIN_DEPTH
    max_depth: Optional[int | float] = MAX_DEPTH

    @field_validator("min_latitude", "max_latitude")
    def validate_latitude(cls, value):
        if value < MIN_LATITUDE or value > MAX_LATITUDE:
            raise ValueError(
                f"La latitude doit être comprise entre {MIN_LATITUDE} et {MAX_LATITUDE}."
            )

        return value

    @field_validator("min_longitude", "max_longitude")
    def validate_longitude(cls, value):
        if value < MIN_LONGITUDE or value > MAX_LONGITUDE:
            raise ValueError(
                f"La longitude doit être comprise entre {MIN_LONGITUDE} et {MAX_LONGITUDE}."
            )

        return value

    @field_validator("min_depth", "max_depth")
    def validate_depth(cls, value):
        if value is not None and value < 0:
            raise ValueError(
                f"La profondeur doit être supérieure ou égale à {MIN_DEPTH}."
            )

        return value


def load_config(config_file: Optional[Path] = CONFIG_FILE) -> DataConfigDict:
    """
    Retournes les données de configuration du fichier TOML.

    :param config_file: (Optional[Path]) Le chemin du fichier de configuration.
    :return: (DataConfigDict) Les données de configuration.
    """
    LOGGER.debug(f"Chargement du fichier de configuration : '{config_file}'.")

    with open(config_file, "r") as file:
        data = toml.load(file)

    return data


def get_data_config(config_file: Optional[Path] = CONFIG_FILE) -> DataFilterConfig:
    """
    Retournes la configuration pour la transformation des données.

    :param config_file: (Optional[Path]) Le chemin du fichier de configuration.
    :return: (DataFilterConfig) La configuration de transformation des données.
    """
    config_data: DataConfigDict = load_config(config_file=config_file)

    LOGGER.debug(
        f"Initialisation de la configuration de pour la transformation des données."
    )

    data_filter: DataFilterDict = config_data["Data"]["Transformation"]["Filter"]

    return DataFilterConfig(
        min_latitude=(
            data_filter["min_latitude"]
            if "min_latitude" in data_filter
            else MIN_LATITUDE
        ),
        max_latitude=(
            data_filter["max_latitude"]
            if "max_latitude" in data_filter
            else MAX_LATITUDE
        ),
        min_longitude=(
            data_filter["min_longitude"]
            if "min_longitude" in data_filter
            else MIN_LONGITUDE
        ),
        max_longitude=(
            data_filter["max_longitude"]
            if "max_longitude" in data_filter
            else MAX_LONGITUDE
        ),
        min_depth=data_filter["min_depth"] if "min_depth" in data_filter else MIN_DEPTH,
        max_depth=data_filter["max_depth"] if "max_depth" in data_filter else MAX_DEPTH,
    )
