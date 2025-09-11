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
    SSP_ERRORS_PATH,
    SSP_ERROR_COEFFICIENT,
)
import schema
from schema import model_ids as schema_ids

LOGGER = logger.bind(name="CSB-Processing.Transformation.Uncertainty")


class TVUConfigProtocol(Protocol):
    """Configuration de géoréférencement des TVU."""

    constant_tvu_wlo: float
    default_constant_tvu_wlp: float
    depth_coefficient_tvu: float
    default_depth_ssp_error_coefficient: float
    max_distance_ssp: float


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
    LOGGER.debug(f"Chargement des incertitudes de WLP par station depuis {json_file}.")

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


def get_ssp_errors(file_path: Path = SSP_ERRORS_PATH) -> gpd.GeoDataFrame:
    """
    Charge les erreurs SSP à partir d'un fichier GeoJSON.

    :param file_path: Chemin vers le fichier contenant les erreurs SSP.
    :type file_path: Path
    :return: GeoDataFrame des erreurs SSP.
    :rtype: gpd.GeoDataFrame
    """
    LOGGER.debug(f"Chargement des erreurs SSP depuis {file_path}.")

    return gpd.read_file(file_path)


def get_equidistant_azimuthal_crs(
    data: gpd.GeoDataFrame,
) -> str:
    """
    Génère une chaîne de définition de projection pour une projection équidistante azimutale

    :param data: GeoDataFrame contenant les données géométriques.
    :type data: gpd.GeoDataFrame
    :return: Chaîne de définition de projection (PROJ string).
    :rtype: str
    """
    # Calcul du centroïde réel des données
    centroid = data.geometry.union_all().centroid
    central_lon, central_lat = centroid.x, centroid.y

    # Création de la chaîne de définition de projection personnalisée (PROJ string)
    proj_str = f"+proj=aeqd +lat_0={central_lat} +lon_0={central_lon} +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"

    LOGGER.debug(
        f"Projection équidistante azimutale centrée sur ({central_lat}, {central_lon})."
    )

    return proj_str


def reproject_to_crs(
    crs: str,
    *data: gpd.GeoDataFrame,
) -> list[gpd.GeoDataFrame]:
    """
    Reprojette plusieurs GeoDataFrames vers une projection donnée.

    :param crs: Chaîne de définition de projection (PROJ string).
    :type crs: str
    :param data: Liste de GeoDataFrames à reprojeter.
    :type data: gpd.GeoDataFrame
    :return: Liste de GeoDataFrames reprojetées.
    :rtype: list[gpd.GeoDataFrame]
    """
    LOGGER.debug(f"Reprojection des données vers le CRS: {crs}.")

    reprojected_gdfs = [gdf.to_crs(crs) for gdf in data]

    return reprojected_gdfs


def filter_data_by_bbox(
    data: gpd.GeoDataFrame,
    bbox: np.ndarray,
    buffer: Optional[float] = 0,
) -> gpd.GeoDataFrame:
    """
    Filtre les erreurs SSP par bounding box avec un buffer optionnel.

    :param data: GeoDataFrame des erreurs SSP à filtrer.
    :type data: gpd.GeoDataFrame
    :param bbox: Bounding box au format [xmin, ymin, xmax, ymax].
    :type bbox: np.ndarray
    :param buffer: Distance de buffer en mètres (défaut: 0).
    :type buffer: float
    :return: GeoDataFrame filtré des erreurs SSP.
    :rtype: gpd.GeoDataFrame
    """
    LOGGER.debug(
        f"Filtrage données par bounding box ({bbox}) avec un buffer de {buffer} mètres."
    )

    return data.cx[
        bbox[0] - buffer : bbox[2] + buffer,
        bbox[1] - buffer : bbox[3] + buffer,
    ]


def perform_spatial_join_with_data(
    data: gpd.GeoDataFrame,
    data_to_join: gpd.GeoDataFrame,
    column_to_join: str,
    max_distance: float,
    fill_nan_value: float,
) -> gpd.GeoDataFrame:
    """
    Effectue la jointure spatiale avec entre 2 GeoDataFrame.

    :param data: Données de base.
    :type data: gpd.GeoDataFrame
    :param data_to_join: Données à joindre.
    :type data_to_join: gpd.GeoDataFrame
    :param column_to_join: Nom de la colonne à joindre.
    :type column_to_join: str
    :param max_distance: Distance maximale pour la jointure spatiale (en mètres).
    :type max_distance: float
    :param fill_nan_value: Valeur pour remplir les NaN après la jointure.
    :type fill_nan_value: float
    :return: Données avec la colonne jointe.
    :rtype: gpd.GeoDataFrame
    """
    LOGGER.debug(
        f"Jointure spatiale de la colonne '{column_to_join}' avec une distance maximale de {max_distance} mètres."
    )

    # Jointure spatiale optimisée
    data_with_join = data.sjoin_nearest(
        data_to_join[[schema_ids.GEOMETRY, column_to_join]],
        how="left",
        max_distance=max_distance,
    )

    # Gestion des valeurs manquantes
    data_with_join[column_to_join] = data_with_join[column_to_join].fillna(
        fill_nan_value
    )

    return data_with_join


def join_with_ssp_errors(
    data: gpd.GeoDataFrame,
    max_distance: float,
    default_ssp_error_coeff: float,
) -> gpd.GeoDataFrame:
    """
    Effectue une jointure spatiale entre les données de bathymétrie et les erreurs SSP.

    :param data: Données brut de profondeur.
    :type data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :param max_distance: Distance maximale pour la jointure spatiale (en mètres).
    :type max_distance: float
    :param default_ssp_error_coeff: Valeur par défaut du coefficient d'erreur SSP si aucune donnée n'est trouvée à proximité.
    :type default_ssp_error_coeff: float
    :return: Données de profondeur avec les erreurs SSP jointes.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    """
    ssp_errors = get_ssp_errors()
    original_crs = data.crs

    # Déterminer si une reprojection est nécessaire
    needs_reprojection = original_crs and original_crs.is_geographic
    data_to_join, ssp_errors_to_join = (
        reproject_to_crs(get_equidistant_azimuthal_crs(data), data, ssp_errors)
        if needs_reprojection
        else (data, ssp_errors)
    )

    ssp_errors_to_join = filter_data_by_bbox(
        data=ssp_errors_to_join, bbox=data_to_join.total_bounds, buffer=max_distance
    )

    LOGGER.debug("Jointure spatiale des données de profondeur avec les erreurs SSP.")
    data_with_ssp = perform_spatial_join_with_data(
        data=data_to_join,
        data_to_join=ssp_errors_to_join,
        column_to_join=SSP_ERROR_COEFFICIENT,
        max_distance=max_distance,
        fill_nan_value=default_ssp_error_coeff,
    )

    # Reprojeter vers le CRS original si nécessaire
    if needs_reprojection:
        data_with_ssp = data_with_ssp.to_crs(original_crs)

    return data_with_ssp


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
    station_mapping = create_uncertainty_mapping()

    data = join_with_ssp_errors(
        data,
        tvu_config.max_distance_ssp,
        tvu_config.default_depth_ssp_error_coefficient,
    )

    LOGGER.debug(f"Calcul du l'incertitude verticale des données de profondeur.")

    depth_component = data[schema_ids.DEPTH_RAW_METER] * (
        (tvu_config.depth_coefficient_tvu + data[SSP_ERROR_COEFFICIENT]) / 100
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
            .fillna(tvu_config.default_constant_tvu_wlp),
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
