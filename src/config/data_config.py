"""
Module de configuration des données.

Ce module contient les classes et fonctions nécessaires pour charger et valider
les configurations de filtrage des données.
"""

from pathlib import Path
from pydantic import BaseModel, field_validator
from typing import Optional

from loguru import logger

from .helper import load_config


LOGGER = logger.bind(name="CSB-Pipeline.Config.DataConfig")

CONFIG_FILE: Path = Path(__file__).parent.parent / "CONFIG_csb-processing.toml"

DataDict = dict[str, int | float]
DataConfigDict = dict[str, dict[str, DataDict]]


MIN_LATITUDE: int | float = -90
MAX_LATITUDE: int | float = 90
MIN_LONGITUDE: int | float = -180
MAX_LONGITUDE: int | float = 180
MIN_DEPTH: int | float = 0
MAX_DEPTH: int | float | None = None


class DataFilterConfig(BaseModel):
    """
    Classe de configuration pour le filtrage des données.

    :param min_latitude: La latitude minimale.
    :type min_latitude: int | float
    :param max_latitude: La latitude maximale.
    :type max_latitude: int | float
    :param min_longitude: La longitude minimale.
    :type min_longitude: int | float
    :param max_longitude: La longitude maximale.
    :type max_longitude: int | float
    :param min_depth: La profondeur minimale.
    :type min_depth: int | float
    :param max_depth: La profondeur maximale.
    :type max_depth: int | float | None
    """

    min_latitude: int | float = MIN_LATITUDE
    """La latitude minimale."""
    max_latitude: int | float = MAX_LATITUDE
    """La latitude maximale."""
    min_longitude: int | float = MIN_LONGITUDE
    """La longitude minimale."""
    max_longitude: int | float = MAX_LONGITUDE
    """La longitude maximale."""
    min_depth: int | float = MIN_DEPTH
    """La profondeur minimale."""
    max_depth: Optional[int | float] = MAX_DEPTH
    """La profondeur maximale."""

    @field_validator("min_latitude", "max_latitude")
    def validate_latitude(cls, value: int | float) -> int | float:
        """
        Valide la latitude.

        :param value: La valeur de la latitude.
        :type value: int | float
        :return: La valeur de la latitude.
        :rtype: int | float
        :raises ValueError: Si la latitude n'est pas comprise entre MIN_LATITUDE et MAX_LATITUDE.
        """
        if value < MIN_LATITUDE or value > MAX_LATITUDE:
            raise ValueError(
                f"La latitude doit être comprise entre {MIN_LATITUDE} et {MAX_LATITUDE}."
            )

        return value

    @field_validator("min_longitude", "max_longitude")
    def validate_longitude(cls, value: int | float) -> int | float:
        """
        Valide la longitude.

        :param value: La valeur de la longitude.
        :type value: int | float
        :return: La valeur de la longitude.
        :rtype: int | float
        :raises ValueError: Si la longitude n'est pas comprise entre MIN_LONGITUDE et MAX_LONGITUDE.
        """
        if value < MIN_LONGITUDE or value > MAX_LONGITUDE:
            raise ValueError(
                f"La longitude doit être comprise entre {MIN_LONGITUDE} et {MAX_LONGITUDE}."
            )

        return value

    @field_validator("min_depth", "max_depth")
    def validate_depth(cls, value: int | float | None) -> int | float | None:
        """
        Valide la profondeur.

        :param value: La valeur de la profondeur.
        :type value: int | float | None
        :return: La valeur de la profondeur.
        :rtype: int | float | None
        :raises ValueError: Si la profondeur est inférieure à MIN_DEPTH.
        """
        if value is not None and value < 0:
            raise ValueError(
                f"La profondeur doit être supérieure ou égale à {MIN_DEPTH}."
            )

        return value


class DataGeoreferenceConfig(BaseModel):
    """
    Classe de configuration pour le géoréférencement des données.

    :param water_level_tolerance: Temps tampon en minutes pour les données de niveau d'eau à récupérer.
    :type water_level_tolerance: int | float
    """

    water_level_tolerance: int | float
    """La tolérance en minutes pour les données de marée à récupérer pour le géoréférencement."""


def get_data_config(
    config_file: Optional[Path] = CONFIG_FILE,
) -> tuple[DataFilterConfig, DataGeoreferenceConfig]:
    """
    Retournes la configuration pour la transformation des données et le géoréférencement.

    :param config_file: Le chemin du fichier de configuration.
    :type config_file: Optional[Path]
    :return: La configuration pour la transformation des données et le géoréférencement.
    :rtype: tuple[DataFilterConfig, DataGeoreferenceConfig]
    """
    config_data: DataConfigDict = load_config(config_file=config_file)["DATA"]

    LOGGER.debug(
        f"Initialisation de la configuration de pour la transformation des données."
    )

    data_filter: DataDict = config_data["Transformation"]["filter"]
    data_georef: DataDict = config_data["Georeference"]["tide"]

    return (
        DataFilterConfig(
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
            min_depth=(
                data_filter["min_depth"] if "min_depth" in data_filter else MIN_DEPTH
            ),
            max_depth=(
                data_filter["max_depth"] if "max_depth" in data_filter else MAX_DEPTH
            ),
        ),
        DataGeoreferenceConfig(
            water_level_tolerance=data_georef["water_level_tolerance"]
        ),
    )
