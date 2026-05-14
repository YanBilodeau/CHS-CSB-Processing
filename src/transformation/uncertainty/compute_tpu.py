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
    DATALOGGER_UNCERTAINTY_JSON,
    UNCERTAINTY_M,
    SSP_ERRORS_PATH,
    SSP_ERROR_COEFFICIENT,
    CONSTANT_THU_KEY,
    CONSTANT_TVU_KEY,
)
import schema
from schema import model_ids as schema_ids
from processing_context import ProcessingContext

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

    with open(json_file, "r", encoding="utf-8-sig") as file:
        data = json.load(file)

    return data


@lru_cache(maxsize=128)
def get_datalogger_uncertainty(
    json_file: Path = DATALOGGER_UNCERTAINTY_JSON,
) -> dict[str, dict[str, float]]:
    """
    Charge les constantes d'incertitude (constant_thu et constant_tvu) par DataLoggerType
    depuis un fichier JSON unique.

    :param json_file: Chemin vers le fichier JSON.
    :type json_file: Path
    :return: Dictionnaire des constantes d'incertitude par DataLoggerType.
    :rtype: dict[str, dict[str, float]]
    """
    LOGGER.debug(
        f"Chargement des constantes d'incertitude par DataLoggerType depuis {json_file}."
    )

    with open(json_file, "r", encoding="utf-8-sig") as file:
        data = json.load(file)

    return data


def _get_constant_for_datalogger(
    datalogger_type: Optional[str],
    key: str,
    default: float,
) -> float:
    """
    Retourne la valeur d'une constante d'incertitude pour un DataLoggerType donné.

    Si le type est présent dans datalogger_uncertainty.json et que la clé demandée
    y figure, cette valeur est retournée (priorité JSON). Sinon, la valeur par défaut
    est utilisée.

    :param datalogger_type: Type de capteur (valeur de DataLoggerType).
    :type datalogger_type: Optional[str]
    :param key: Clé de la constante à récupérer (ex. ``constant_thu``, ``constant_tvu``).
    :type key: str
    :param default: Valeur par défaut si le type ou la clé est absent du JSON.
    :type default: float
    :return: Valeur de la constante à appliquer.
    :rtype: float
    """
    if datalogger_type is None:
        return default

    entry = get_datalogger_uncertainty().get(datalogger_type)
    if entry is not None:
        constant = entry.get(key)
        if constant is not None:
            LOGGER.debug(
                f"{key} pour '{datalogger_type}' trouvée dans le JSON : {constant}."
            )
            return float(constant)

    LOGGER.debug(
        f"DataLoggerType '{datalogger_type}' absent du JSON ({key}) — "
        f"utilisation de la valeur par défaut : {default}."
    )

    return default


def get_constant_thu_for_datalogger(
    datalogger_type: Optional[str],
    default: float,
) -> float:
    """
    Retourne la valeur de constant_thu pour un DataLoggerType donné.

    Si le type est présent dans datalogger_uncertainty.json (clé ``constant_thu``),
    cette valeur est retournée (priorité JSON). Sinon, la valeur par défaut fournie
    (issue du TOML) est utilisée.

    :param datalogger_type: Type de capteur (valeur de DataLoggerType).
    :type datalogger_type: Optional[str]
    :param default: Valeur par défaut si le type est absent du JSON.
    :type default: float
    :return: Valeur de constant_thu à appliquer.
    :rtype: float
    """
    return _get_constant_for_datalogger(datalogger_type, CONSTANT_THU_KEY, default)


def get_constant_tvu_for_datalogger(
    datalogger_type: Optional[str],
    default: float,
) -> float:
    """
    Retourne la valeur de constant_tvu pour un DataLoggerType donné.

    Utilisée uniquement quand ``already_at_chart_datum=True``. Si le type est présent
    dans datalogger_uncertainty.json (clé ``constant_tvu``), cette valeur est retournée
    (priorité JSON). Sinon, la valeur par défaut fournie est utilisée.

    :param datalogger_type: Type de capteur (valeur de DataLoggerType).
    :type datalogger_type: Optional[str]
    :param default: Valeur par défaut si le type est absent du JSON.
    :type default: float
    :return: Valeur de constant_tvu à appliquer.
    :rtype: float
    """
    return _get_constant_for_datalogger(datalogger_type, CONSTANT_TVU_KEY, default)


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
    apply_water_level: bool = True,
    processing_context: Optional[ProcessingContext] = None,
) -> gpd.GeoDataFrame:
    """
    Calcule le TVU des données de bathymétrie.

    :param data: Données brut de profondeur.
    :type data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :param decimal_precision: Précision décimale pour les valeurs de TVU.
    :type decimal_precision: int
    :param tvu_config: Configuration des paramètres du TVU.
    :type tvu_config: TVUConfigProtocol
    :param apply_water_level: Si ``True``, la composante station est dérivée du mapping
        par zone de marée (WLO/WLP). Si ``False``, une constante fixe (0.0) est utilisée.
    :type apply_water_level: bool
    :param processing_context: Contexte de traitement. Si ``already_at_chart_datum=True``,
        résout la constante TVU depuis ``datalogger_uncertainty.json`` et force
        l'utilisation de la constante (indépendamment de ``apply_water_level``).
    :type processing_context: Optional[ProcessingContext]
    :return: Données de profondeur avec le TVU.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    """
    already_at_chart_datum: bool = (
        processing_context.already_at_chart_datum
        if processing_context is not None
        else False
    )
    # Décision explicite : constante fixe ou composante par station
    use_constant: bool = not apply_water_level or already_at_chart_datum

    LOGGER.debug(
        f"TVU — mode : {'constante fixe' if use_constant else 'mapping par station'} "
        f"(apply_water_level={apply_water_level}, already_at_chart_datum={already_at_chart_datum})."
    )

    # Résoudre la constante inconditionnellement pour éviter une variable potentiellement
    # non définie ; la valeur n'est utilisée que si use_constant=True.
    constant_tvu: float = 0.0
    if already_at_chart_datum and processing_context is not None:
        constant_tvu = processing_context.resolve_constant_tvu(default=0.0)
        LOGGER.debug(
            f"TVU — constante résolue depuis ProcessingContext "
            f"(datalogger_type={processing_context.datalogger_type}) : {constant_tvu}."
        )

    # station_mapping = create_uncertainty_mapping()

    data = join_with_ssp_errors(
        data,
        tvu_config.max_distance_ssp,
        tvu_config.default_depth_ssp_error_coefficient,
    )

    LOGGER.debug(f"Calcul du l'incertitude verticale des données de profondeur.")

    depth_component = data[schema_ids.DEPTH_RAW_METER] * (
        (tvu_config.depth_coefficient_tvu + data[SSP_ERROR_COEFFICIENT]) / 100
    )

    dc = np.asarray(depth_component)
    LOGGER.debug(
        f"TVU — depth_component : min={dc.min():.4f}, max={dc.max():.4f}, mean={dc.mean():.4f} "
        f"(depth_coefficient_tvu={tvu_config.depth_coefficient_tvu}, "
        f"ssp_coeff min={data[SSP_ERROR_COEFFICIENT].min():.4f} / max={data[SSP_ERROR_COEFFICIENT].max():.4f})."
    )

    station_component = (
        constant_tvu
        if use_constant
        else np.where(
            data[schema_ids.TIME_SERIE].str.contains("wlo", case=False, na=False)
            & ~data[schema_ids.TIME_SERIE].str.contains("wlp", case=False, na=False),
            tvu_config.constant_tvu_wlo,
            data[schema_ids.TIDE_ZONE_CODE]
            .map(create_uncertainty_mapping())
            .fillna(tvu_config.default_constant_tvu_wlp),
        )
    )

    if use_constant:
        LOGGER.debug(f"TVU — station_component : constante fixe = {constant_tvu}.")
    else:
        sc = np.asarray(station_component)
        LOGGER.debug(
            f"TVU — station_component : mapping par station — "
            f"min={sc.min():.4f}, max={sc.max():.4f}, mean={sc.mean():.4f} "
            f"(wlo={tvu_config.constant_tvu_wlo}, défaut wlp={tvu_config.default_constant_tvu_wlp})."
        )

    data.loc[:, schema_ids.UNCERTAINTY] = (depth_component + station_component).round(
        decimal_precision
    )

    data[schema_ids.UNCERTAINTY_STATION_METER] = np.round(
        station_component, decimal_precision
    )
    data[schema_ids.SSP_UNCERTAINTY_PERCENT] = np.round(
        data[SSP_ERROR_COEFFICIENT], decimal_precision
    )

    return data


def compute_thu(
    data: gpd.GeoDataFrame,
    decimal_precision: int,
    thu_config: THUConfigProtocol,
    processing_context: Optional[ProcessingContext] = None,
) -> gpd.GeoDataFrame:
    """
    Calcule le THU des données de bathymétrie.

    :param data: Données brut de profondeur.
    :type data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :param decimal_precision: Précision décimale pour les valeurs de THU.
    :type decimal_precision: int
    :param thu_config: Configuration des paramètres du THU.
    :type thu_config: THUConfigProtocol
    :param processing_context: Contexte de traitement. Si le type de capteur est présent
        dans ``datalogger_uncertainty.json``, la valeur ``constant_thu`` du JSON est utilisée
        en priorité sur celle du TOML.
    :type processing_context: Optional[ProcessingContext]
    :return: Données de profondeur avec le THU.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    """
    LOGGER.debug(f"Calcul de l'incertitude horizontale des données de profondeur.")

    if processing_context is not None:
        constant_thu: float = processing_context.resolve_constant_thu(
            thu_config.constant_thu
        )
        # resolve_constant_thu logue déjà la source (JSON vs défaut TOML) ;
        # on confirme ici la valeur effective retenue.
        LOGGER.debug(
            f"THU — constant_thu résolu depuis ProcessingContext "
            f"(datalogger_type={processing_context.datalogger_type}) : {constant_thu} "
            f"(TOML défaut = {thu_config.constant_thu})."
        )
    else:
        constant_thu = thu_config.constant_thu
        LOGGER.debug(
            f"THU — constant_thu depuis TOML (pas de ProcessingContext) : {constant_thu}."
        )

    thu_depth_coeficient: float = np.tan(np.radians(thu_config.cone_angle_sonar) / 2)
    LOGGER.debug(
        f"THU — cone_angle_sonar={thu_config.cone_angle_sonar}° → "
        f"thu_depth_coeficient={thu_depth_coeficient:.6f}."
    )

    data.loc[:, schema_ids.THU] = round(
        (data[schema_ids.DEPTH_RAW_METER] * thu_depth_coeficient) + constant_thu,
        decimal_precision,
    )

    thu_vals = data[schema_ids.THU]
    LOGGER.debug(
        f"THU — résultat : min={thu_vals.min():.4f}, max={thu_vals.max():.4f}, "
        f"mean={thu_vals.mean():.4f}."
    )

    return data
