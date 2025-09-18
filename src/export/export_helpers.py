"""
Module d'exportation des données traitées.

Ce module contient des fonctions utilitaires pour finaliser, séparer et exporter les données traitées.
"""

import concurrent.futures
from pathlib import Path
from typing import Optional, Collection

import geopandas as gpd
import pandas as pd
from loguru import logger

from schema import model_ids as schema_ids
import schema
from .factory_export import FileTypes, export_geodataframe


LOGGER = logger.bind(name="CSB-Processing.Export.Helpers")


def get_export_file_name(
    data_geodataframe: gpd.GeoDataFrame,
    datalogger_type: str,
    vessel_name: Optional[str],
) -> str:
    """
    Récupère le nom du fichier d'exportation.

    :param data_geodataframe: Données traitées à exporter.
    :type data_geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema]
    :param datalogger_type: Type de capteur.
    :type datalogger_type: str
    :param vessel_name: Nom du navire.
    :type vessel_name: Optional[str]
    :return: Nom du fichier d'exportation.
    :rtype: str
    """
    return (
        f"CH-"
        f"{datalogger_type}-"
        f"{vessel_name if vessel_name else 'Unknown'}-"
        f"{data_geodataframe[schema_ids.TIME_UTC].min().strftime('%Y%m%d')}-"
        f"{data_geodataframe[schema_ids.TIME_UTC].max().strftime('%Y%m%d')}"
    )


def finalize_geodataframe(data_geodataframe: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Finalise le GeoDataFrame des données.

    :param data_geodataframe: GeoDataFrame des données.
    :type data_geodataframe: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :return: GeoDataFrame des données finalisé.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerSchema]
    """
    LOGGER.debug(f"Finalisation du GeoDataFrame des données.")

    # Création vectorisée des objets WaterLevelInfo
    water_level_infos = [
        schema.WaterLevelInfo(
            water_level_meter=wl_meter,
            time_series=ts,
            id=zone_id,
            code=zone_code,
            name=zone_name,
        )
        for wl_meter, ts, zone_id, zone_code, zone_name in zip(
            data_geodataframe[schema_ids.WATER_LEVEL_METER],
            data_geodataframe[schema_ids.TIME_SERIE],
            data_geodataframe[schema_ids.TIDE_ZONE_ID],
            data_geodataframe[schema_ids.TIDE_ZONE_CODE],
            data_geodataframe[schema_ids.TIDE_ZONE_NAME],
        )
    ]

    data_geodataframe[schema_ids.WATER_LEVEL_INFO] = water_level_infos

    return data_geodataframe[schema.DataLoggerSchema.__annotations__.keys()]


def split_data_by_iho_order(
    data_geodataframe: gpd.GeoDataFrame,
) -> dict[str, gpd.GeoDataFrame]:
    """
    Regroupe et sépare le GeoDataFrame par ordre IHO.

    :param data_geodataframe: Le GeoDataFrame à séparer.
    :type data_geodataframe: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :return: Un dictionnaire contenant les GeoDataFrames séparés par ordre IHO.
    :rtype: dict[str, gpd.GeoDataFrame]
    """
    LOGGER.debug(f"Séparation du GeoDataFrame par ordre de levé OHI.")

    grouped_data = {}
    for iho_order, group in data_geodataframe.groupby(
        schema_ids.IHO_ORDER
    ):  # todo : dropna=False ?
        key = "NAN" if pd.isna(iho_order) else str(iho_order)
        grouped_data[key] = group
        LOGGER.debug(f"Ordre IHO {iho_order}: {len(group):,} sondes")

    LOGGER.debug(f"Ordre IHO : {grouped_data.keys()}")

    return grouped_data


def export_processed_data(
    data_geodataframe: gpd.GeoDataFrame,
    output_data_path: Path,
    file_type: FileTypes,
    resolution: float,
    **kwargs,
) -> None:
    """
    Exporte les données traitées dans un fichier GeoPackage.

    :param data_geodataframe: Données traitées à exporter.
    :type data_geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema]
    :param output_data_path: Chemin du répertoire d'exportation.
    :type output_data_path: Path
    :param file_type: Type de fichier de sortie.
    :type file_type: FileTypes
    :param resolution: Résolution pour les formats raster.
    :type resolution: float
    """
    if file_type == FileTypes.CSAR and "config_caris" not in kwargs:
        LOGGER.warning(
            "La configuration de l'API Caris est requise pour exporter les données au format CSAR."
        )

    logger.info(
        f"Exportation des données traitées ({len(data_geodataframe):,} sondes) au format {file_type} : {output_data_path}."
    )

    try:
        export_geodataframe(
            geodataframe=data_geodataframe,
            file_type=file_type,
            output_path=output_data_path,
            resolution=resolution,
            **kwargs,
        )
        LOGGER.success(
            f"Exportation des données traitées au format {file_type} complété : {output_data_path}."
        )

    except Exception as error:
        LOGGER.error(
            f"Erreur lors de l'exportation des données au format {file_type} : {error}."
        )


def export_processed_data_to_file_types(
    data_geodataframe: gpd.GeoDataFrame,
    output_base_path: Path,
    file_types: Collection[FileTypes],
    resolution: Optional[float] = 0.00005,
    groub_by_iho_order: Optional[bool] = True,
    **kwargs,
) -> None:
    """
    Exporte les données traitées dans plusieurs formats de fichier.

    :param data_geodataframe: Données traitées à exporter.
    :type data_geodataframe: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :param output_base_path: Chemin de base pour les fichiers d'exportation.
    :type output_base_path: Path
    :param file_types: Liste des types de fichiers de sortie.
    :type file_types: Collection[FileTypes]
    :param resolution: Résolution pour les formats raster.
    :type resolution: float
    :param groub_by_iho_order: Regrouper les données par ordre IHO.
    :type groub_by_iho_order: bool
    """
    grouped_data: dict[str | None, gpd.GeoDataFrame] = {"ALL": data_geodataframe}

    if groub_by_iho_order:
        iho_order_data: dict[str | None, gpd.GeoDataFrame] = split_data_by_iho_order(
            data_geodataframe=data_geodataframe
        )
        grouped_data.update(iho_order_data)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        for group_key, group_df in grouped_data.items():
            if group_df.empty:
                continue

            suffix = "" if group_key == "ALL" else f"_{group_key}"
            output_path = output_base_path.with_name(f"{output_base_path.name}{suffix}")

            for file_type in file_types:
                executor.submit(
                    export_processed_data,
                    data_geodataframe=group_df,
                    output_data_path=output_path,
                    file_type=file_type,
                    resolution=resolution,
                    **kwargs,
                )
