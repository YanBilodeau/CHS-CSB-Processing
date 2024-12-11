"""
Module de configuration de l'API IWLS.

Ce module contient les classes et fonctions nécessaires pour charger et valider
la configuration de l'API IWLS.
"""

import re
from datetime import timedelta
from pathlib import Path
from typing import Optional

from loguru import logger
from pydantic import BaseModel, field_validator

import iwls_api_request as iwls

LOGGER = logger.bind(name="CSB-Pipeline.Config.IWLSAPIConfig")

CONFIG_FILE: Path = Path(__file__).parent.parent / "CONFIG_csb-processing.toml"

TimeSeriesDict = dict[str, list[str]]
IWLSapiDict = dict[
    str, dict[str, TimeSeriesDict | iwls.EnvironmentDict | iwls.ProfileDict]
]


class TimeSeriesConfig(BaseModel):
    """
    Classe de configuration pour les séries temporelles.

    :param priority: La liste des séries temporelles à garder par ordre de priorité.
    :type priority: list[iwls.TimeSeries]
    :param max_time_gap: Le temps maximal permit entre deux points.
    :type max_time_gap: str | None
    :param threshold_interpolation_filling: Le seuil de remplissage ou d'interpolation.
    :type threshold_interpolation_filling: str | None
    :param wlo_qc_flag_filter: Les filtres de qualité à filtrer.
    :type wlo_qc_flag_filter: list[str] | None
    :param buffer_time: Le temps de buffer à ajouter s'il manque des données pour l'interpolation.
    :type buffer_time: timedelta | None
    """

    priority: list[iwls.TimeSeries]
    """La liste des séries temporelles à garder par ordre de priorité."""
    max_time_gap: str | None
    """Le temps maximal permit entre deux points."""
    threshold_interpolation_filling: str | None
    """Le seuil de remplissage ou d'interpolation."""
    wlo_qc_flag_filter: list[str] | None
    """Les filtres de qualité à filtrer."""
    buffer_time: timedelta | None
    """Le temps de buffer à ajouter s'il manque des données pour l'interpolation."""

    def __init__(self, **data):
        super().__init__(**data)
        if isinstance(data.get("buffer_time"), int):
            self.buffer_time = timedelta(hours=data["buffer_time"])

    @field_validator("max_time_gap", "threshold_interpolation_filling")
    def validate_time_gap(cls, value: str | None) -> str | None:
        """
        Valide le time gap.

        :param value: Le time gap.
        :type value: str | None
        :return: Le time gap.
        :rtype: str | None
        :raises ValueError: Si le time gap n'est pas au bon format.
        """
        if value == "":
            return None

        if value is not None:
            pattern = re.compile(r"^\d+\s*(min|h)$")
            if not pattern.match(value):
                raise ValueError(
                    'Le time gap doit être au format "<number> <minutes|hours>".'
                )

        return value


class CacheConfig(BaseModel):
    """
    Classe de configuration pour le cache.

    :param cache_path: Le répertoire du cache.
    :type cache_path: Path
    :param ttl: Le temps de vie du cache en secondes.
    :type ttl: int
    """

    cache_path: Optional[Path]
    """Le répertoire du cache."""
    ttl: Optional[int] = 86400  # 24 heures
    """Le temps de vie du cache en secondes."""

    def __init__(self, **data):
        if "cache_path" not in data:
            data["cache_path"] = Path(__file__).parent.parent / "cache"
        super().__init__(**data)

    @field_validator("cache_path")
    def validate_cache_path(cls, value: Path) -> Path:
        """
        Valide le répertoire du cache.

        :param value: Le répertoire du cache.
        :type value: Path
        :return: Le répertoire du cache.
        """
        if not value.exists():
            value.mkdir(parents=True)

        return value

    @field_validator("ttl")
    def validate_ttl(cls, value: int) -> int:
        """
        Valide le temps de vie de la cache.

        :param value: Le temps de vie du cache.
        :type value: int
        :return: Le temps de vie du cache.
        :rtype: int
        :raises ValueError: Si le temps de vie du cache est négatif.
        """
        if value < 0:
            raise ValueError("Le temps de vie du cache doit être positif.")

        return value


class IWLSAPIConfig(BaseModel):
    """
    Classe de configuration pour l'API IWLS.

    :param dev: L'environnement de développement.
    :type dev: iwls.APIEnvironment | None
    :param prod: L'environnement de production.
    :type prod: iwls.APIEnvironment | None
    :param public: L'environnement public.
    :type public: iwls.APIEnvironment | None
    :param time_series: La configuration des séries temporelles.
    :type time_series: TimeSeriesConfig
    :param profile: Le profil actif de l'API.
    :type profile: iwls.APIProfile
    :param cache: La configuration du cache.
    :type cache: CacheConfig
    """

    dev: Optional[iwls.APIEnvironment]
    """Environnement de développement."""
    prod: Optional[iwls.APIEnvironment]
    """Environnement de production."""
    public: Optional[iwls.APIEnvironment]
    """Environnement public."""
    time_series: TimeSeriesConfig
    """Configuration des séries temporelles."""
    profile: iwls.APIProfile
    """Profil actif de l'API."""
    cache: CacheConfig
    """Configuration du cache."""


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
        config_data["IWLS"]["API"]["Environment"]
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
        profile=iwls.APIProfile(**config_data["IWLS"]["API"]["Profile"]),
        cache=(
            CacheConfig(**config_data["IWLS"]["API"]["Cache"])
            if "Cache" in config_data["IWLS"]["API"]
            else CacheConfig()
        ),
    )
