"""
Module pour le calcul des incertitudes verticales (TVU) et horizontales (THU)
des données de bathymétrie.

Ce module utilise des fonctions parallèles pour traiter les données efficacement
en tirant parti de tous les cœurs CPU disponibles.
"""

from pathlib import Path
from functools import lru_cache
from typing import Optional, Protocol
import json

import geopandas as gpd
import numpy as np
from loguru import logger

from .ids_uncertainty import (
    STATION_UNCERTAINTY_JSON,
    UNCERTAINTY_M,
)
import schema
from schema import model_ids as schema_ids

LOGGER = logger.bind(name="CSB-Processing.Transformation.Uncertainty")


class TVUConfigProtocol(Protocol):
    """Configuration de géoréférencement des TVU."""

    constant_tvu_wlo: float
    constant_tvu_wlp: float
    depth_coefficient_tvu: float


class THUConfigProtocol(Protocol):
    """Configuration de géoréférencement des THU."""

    cone_angle_sonar: float
    constant_thu: float


@lru_cache(maxsize=128)
def get_station_uncertainty(
    json_file: Path = STATION_UNCERTAINTY_JSON,
) -> dict[str, dict[str, str | float]]:
    """
    Charge les valeurs d'incertitude par station à partir d'un fichier JSON.

    :param json_file: Chemin vers le fichier JSON contenant les valeurs d'incertitude par station.
    :type json_file: Path
    :return: Dictionnaire des valeurs d'incertitude par station.
    :rtype: dict[str, dict[str, str | float]]
    """
    with open(json_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    return data


def create_uncertainty_mapping() -> dict[str, float]:
    """
    Crée un mapping des codes de station vers leurs valeurs d'incertitude.

    :return: Dictionnaire mappant les codes de station aux valeurs d'incertitude.
    :rtype: dict[str, float]
    """
    station_uncertainty_data = get_station_uncertainty()

    return {
        code: info[UNCERTAINTY_M] for code, info in station_uncertainty_data.items()
    }


def compute_tvu(
    data: gpd.GeoDataFrame,
    decimal_precision: int,
    tvu_config: TVUConfigProtocol,
    constant_tvu: Optional[float] = None,
) -> gpd.GeoDataFrame:
    """
    Calcule le TVU des données de bathymétrie.

    :param data: Données brut de profondeur.
    :type data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :param decimal_precision: Précision décimale pour les valeurs de TVU.
    :type decimal_precision: int
    :param tvu_config: Configuration des paramètres du TVU.
    :type tvu_config: TVUConfigProtocol
    :param constant_tvu: Constante du TVU. Si None, utilise la valeur par station.
    :type constant_tvu: Optional[float]
    :return: Données de profondeur avec le TVU.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    """
    LOGGER.debug(f"Calcul du l'incertitude verticale des données de profondeur.")

    station_mapping = create_uncertainty_mapping()

    depth_component = data[schema_ids.DEPTH_RAW_METER] * (
        tvu_config.depth_coefficient_tvu / 100
    )

    station_component = (
        constant_tvu
        if constant_tvu is not None
        else np.where(
            data[schema_ids.TIME_SERIE].str.contains("wlo", case=False, na=False)
            & ~data[schema_ids.TIME_SERIE].str.contains("wlp", case=False, na=False),
            tvu_config.constant_tvu_wlo,
            data[schema_ids.TIDE_ZONE_CODE]
            .map(station_mapping)
            .fillna(tvu_config.constant_tvu_wlp),
        )
    )

    data.loc[:, schema_ids.UNCERTAINTY] = (depth_component + station_component).round(
        decimal_precision
    )

    return data


def compute_thu(
    data: gpd.GeoDataFrame,
    decimal_precision: int,
    thu_config: THUConfigProtocol,
) -> gpd.GeoDataFrame:
    """
    Calcule le THU des données de bathymétrie.

    :param data: Données brut de profondeur.
    :type data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :param decimal_precision: Précision décimale pour les valeurs de THU.
    :type decimal_precision: int
    :param thu_config: Configuration des paramètres du THU.
    :type thu_config: THUConfigProtocol
    :return: Données de profondeur avec le THU.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    """
    LOGGER.debug(f"Calcul de l'incertitude horizontale des données de profondeur.")
    thu_depth_coeficient: float = np.tan(np.radians(thu_config.cone_angle_sonar) / 2)

    data.loc[:, schema_ids.THU] = round(
        (data[schema_ids.DEPTH_RAW_METER] * thu_depth_coeficient)
        + thu_config.constant_thu,
        decimal_precision,
    )

    return data
