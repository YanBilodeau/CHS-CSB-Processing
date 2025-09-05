"""
Module pour le calcul des incertitudes verticales (TVU) et horizontales (THU)
des données de bathymétrie.

Ce module utilise des fonctions parallèles pour traiter les données efficacement
en tirant parti de tous les cœurs CPU disponibles.
"""

from multiprocessing import cpu_count
from pathlib import Path
from functools import lru_cache
from typing import Optional
import json

import geopandas as gpd
import numpy as np
from loguru import logger

from ..parallel_computing import run_dask_function_in_parallel
from .ids_uncertainty import (
    STATION_UNCERTAINTY_JSON,
    DEFAULT_CONSTANT_TVU,
    UNCERTAINTY_M,
)
import schema
from schema import model_ids as schema_ids

LOGGER = logger.bind(name="CSB-Processing.Transformation.Uncertainty")

CPU_COUNT: int = cpu_count()


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
    depth_coeficient_tvu: float = 0.04,
    constant_tvu: Optional[float] = None,
) -> gpd.GeoDataFrame:
    """
    Calcule le TVU des données de bathymétrie.

    :param data: Données brut de profondeur.
    :type data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :param decimal_precision: Précision décimale pour les valeurs de TVU.
    :type decimal_precision: int
    :param depth_coeficient_tvu: Coefficient de profondeur.
    :type depth_coeficient_tvu: float
    :param constant_tvu: Constante du TVU. Si None, utilise la valeur par station.
    :type constant_tvu: Optional[float]
    :return: Données de profondeur avec le TVU.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    """
    LOGGER.debug(
        f"Calcul du l'incertitude verticale des données de profondeur avec {CPU_COUNT} processus en parallèle."
    )

    station_mapping = create_uncertainty_mapping()

    def calculate_vertical_uncertainty(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        depth_component = gdf[schema_ids.DEPTH_RAW_METER] * depth_coeficient_tvu

        station_component = (
            constant_tvu
            if constant_tvu is not None
            else gdf[schema_ids.TIDE_ZONE_CODE]
            .map(station_mapping)
            .fillna(DEFAULT_CONSTANT_TVU)
        )

        gdf.loc[:, schema_ids.UNCERTAINTY] = (
            depth_component + station_component
        ).round(decimal_precision)

        return gdf

    return run_dask_function_in_parallel(data=data, func=calculate_vertical_uncertainty)


def compute_thu(
    data: gpd.GeoDataFrame,
    decimal_precision: int,
    angular_opening: float = 20.0,
    constant_thu: float = 3.0,
) -> gpd.GeoDataFrame:
    """
    Calcule le THU des données de bathymétrie.

    :param data: Données brut de profondeur.
    :type data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :param decimal_precision: Précision décimale pour les valeurs de THU.
    :type decimal_precision: int
    :param angular_opening: Ouverture angulaire du sondeur.
    :type angular_opening: float
    :param constant_thu: Constante du TPU.
    :type constant_thu: float
    :return: Données de profondeur avec le THU.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    """
    LOGGER.debug(
        f"Calcul de l'incertitude horizontale des données de profondeur avec {CPU_COUNT} processus en parallèle."
    )
    thu_depth_coeficient: float = np.tan(np.radians(angular_opening) / 2)

    def calculate_horizontal_uncertainty(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        gdf.loc[:, schema_ids.THU] = round(
            (gdf[schema_ids.DEPTH_RAW_METER] * thu_depth_coeficient) + constant_thu,
            decimal_precision,
        )
        return gdf

    return run_dask_function_in_parallel(
        data=data, func=calculate_horizontal_uncertainty
    )
