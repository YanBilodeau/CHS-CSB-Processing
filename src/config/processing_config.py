"""
Module de configuration des données.

Ce module contient les classes et fonctions nécessaires pour charger et valider
les configurations de filtrage des données.
"""

from enum import StrEnum
from pathlib import Path
from pydantic import BaseModel, field_validator
from typing import Optional, Any

from loguru import logger

from .helper import load_config


LOGGER = logger.bind(name="Config.ProcessingConfig")

CONFIG_FILE: Path = Path(__file__).parent.parent / "CONFIG_csb-processing.toml"

ConfigDict = dict[str, int | float | str]
CSBconfigDict = dict[str, dict[str, dict[str, ConfigDict]]]


MIN_LATITUDE: int | float = -90
MAX_LATITUDE: int | float = 90
MIN_LONGITUDE: int | float = -180
MAX_LONGITUDE: int | float = 180
MIN_DEPTH: int | float = 0
MAX_DEPTH: int | float | None = None

WATER_LEVEL_TOLERANCE: int | float = 15

INFO: str = "INFO"


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

    :param water_level_tolerance: Écart maximal en minutes entre les données et les niveaux d'eau à
                                récupérer pour le géoréférencement.
    :type water_level_tolerance: int | float
    """

    water_level_tolerance: int | float = WATER_LEVEL_TOLERANCE
    """La tolérance en minutes pour les données de marée à récupérer pour le géoréférencement."""


class VesselConfigManagerType(StrEnum):
    """
    Enumération des types de gestionnaire de configuration de navires.
    """

    VesselConfigJsonManager = "VesselConfigJsonManager"
    """Gestionnaire de configuration de navires en JSON."""
    VesselConfigSQLiteManager = "VesselConfigSQLiteManager"
    """Gestionnaire de configuration de navires en SQLite."""


class VesselManagerConfig(BaseModel):
    """
    Classe de configuration pour le gestionnaire de navires.

    :param manager_type: Le type de gestionnaire de configuration de navires.
    :type manager_type: VesselConfigManagerType
    :param kwargs: Les arguments pour le gestionnaire de configuration de navires.
    :type kwargs: dict[str, Any]
    """

    manager_type: Optional[VesselConfigManagerType]
    kwargs: Optional[dict[str, Any]] = None


class OptionsConfig(BaseModel):
    """
    Classe de configuration pour les options de traitement.
    """

    log_level: str = INFO
    """Le niveau de log."""


class CSBprocessingConfig(BaseModel):
    filter: DataFilterConfig
    georeference: DataGeoreferenceConfig
    vessel_manager: Optional[VesselManagerConfig]
    options: OptionsConfig = OptionsConfig()


def get_data_config(
    config_file: Optional[Path] = CONFIG_FILE,
) -> CSBprocessingConfig:
    """
    Retournes la configuration pour la transformation des données et le géoréférencement.

    :param config_file: Le chemin du fichier de configuration.
    :type config_file: Optional[Path]
    :return: La configuration pour la transformation des données et le géoréférencement.
    :rtype: tuple[DataFilterConfig, DataGeoreferenceConfig]
    """
    config_data: CSBconfigDict = load_config(config_file=config_file)

    LOGGER.debug(
        f"Initialisation de la configuration de pour la transformation des données."
    )

    data_filter: ConfigDict = (
        config_data.get("DATA", {}).get("Transformation", {}).get("filter")
    )
    data_georef: ConfigDict = (
        config_data.get("DATA", {}).get("Georeference", {}).get("water_level")
    )
    vessel_config: ConfigDict = (
        config_data.get("CSB", {}).get("Processing", {}).get("vessel")
    )
    options_config: ConfigDict = (
        config_data.get("CSB", {}).get("Processing", {}).get("options")
    )

    return CSBprocessingConfig(
        filter=(
            DataFilterConfig(
                min_latitude=(data_filter.get("min_latitude") or MIN_LATITUDE),
                max_latitude=(data_filter.get("max_latitude") or MAX_LATITUDE),
                min_longitude=(data_filter.get("min_longitude") or MIN_LONGITUDE),
                max_longitude=(data_filter.get("max_longitude") or MAX_LONGITUDE),
                min_depth=(data_filter.get("min_depth") or MIN_DEPTH),
                max_depth=(data_filter.get("max_depth") or MAX_DEPTH),
            )
            if data_filter
            else DataFilterConfig()
        ),
        georeference=(
            DataGeoreferenceConfig(**data_georef)
            if data_georef
            else DataGeoreferenceConfig()
        ),
        vessel_manager=(
            VesselManagerConfig(
                manager_type=(
                    VesselConfigManagerType(vessel_config["manager_type"])
                    if "manager_type" in vessel_config
                    else None
                ),
                kwargs={
                    key: value
                    for key, value in vessel_config.items()
                    if key != "manager_type"
                },
            )
            if vessel_config
            else None
        ),
        options=(
            OptionsConfig(**options_config) if options_config else OptionsConfig()
        ),
    )
