"""
Module de conversion des données géospatiales.

Ce module contient des fonctions pour convertir les données entre différents formats
avec validation de schéma et configuration.
"""

import concurrent.futures
from pathlib import Path
from typing import Collection, Optional, Tuple

import geopandas as gpd
import i18n
from loguru import logger

import config
import export
import schema
from logger.loguru_config import configure_logger


LOGGER = logger.bind(name="CSB-Processing.Converter")
configure_logger()

CONFIG_FILE: Path = Path(__file__).parent / "CONFIG_csb-processing.toml"


def read_geospatial_file(input_file_path: Path) -> Optional[gpd.GeoDataFrame]:
    """
    Lit un fichier géospatial (GPKG ou GeoJSON) et retourne un GeoDataFrame.

    :param input_file_path: Chemin du fichier géospatial d'entrée.
    :type input_file_path: Path
    :return: GeoDataFrame lu ou None en cas d'erreur.
    :rtype: Optional[gpd.GeoDataFrame[schema.DataLoggerSchema]]
    """
    if not input_file_path.exists():
        LOGGER.error(i18n.t("converter.file_not_found", path=input_file_path))
        return None

    supported_extensions = {".gpkg", ".geojson"}
    if input_file_path.suffix.lower() not in supported_extensions:
        LOGGER.error(
            i18n.t(
                "converter.unsupported_format",
                suffix=input_file_path.suffix,
                formats=supported_extensions,
            )
        )
        return None

    LOGGER.info(i18n.t("converter.reading_file", path=input_file_path))

    try:
        data_geodataframe: gpd.GeoDataFrame = gpd.read_file(input_file_path)

        LOGGER.success(
            i18n.t("converter.file_read_success", count=f"{len(data_geodataframe):,}")
        )

        if data_geodataframe.empty:
            LOGGER.warning(i18n.t("converter.file_empty"))
            return None

        schema.validate_schema(data_geodataframe, schema.DataLoggerSchema)

        return data_geodataframe

    except Exception as error:
        LOGGER.error(i18n.t("converter.file_read_error", error=error))
        return None


def load_configurations(
    config_path: Path, file_types: Collection[config.FileTypes]
) -> Tuple[Optional[config.CSBprocessingConfig], Optional[config.CarisAPIConfig]]:
    """
    Charge les configurations nécessaires pour l'exportation.

    :param config_path: Chemin du fichier de configuration.
    :type config_path: Path
    :param file_types: Types de fichiers à exporter.
    :type file_types: Collection[config.FileTypes]
    :return: Tuple contenant la configuration de traitement et la configuration Caris.
    :rtype: Tuple[Optional[config.CSBprocessingConfig], Optional[config.CarisAPIConfig]]
    """
    if not config_path.exists():
        LOGGER.warning(i18n.t("converter.config_not_found"))

        if config.FileTypes.CSAR in file_types:
            LOGGER.error(i18n.t("converter.caris_config_required"))

        return None, None

    LOGGER.info(i18n.t("converter.loading_config", path=config_path))

    try:
        processing_config = config.get_data_config(config_file=config_path)
        caris_api_config = None

        if not config.FileTypes.CSAR in file_types:
            return processing_config, caris_api_config

        try:
            caris_api_config = config.get_caris_api_config(config_file=config_path)

        except config.CarisConfigError as error:
            LOGGER.error(i18n.t("converter.caris_config_error", error=error))
            return None, None

        return processing_config, caris_api_config

    except Exception as error:
        LOGGER.error(i18n.t("converter.config_load_error", error=error))
        return None, None


def export_to_file_types(
    data_geodataframe: gpd.GeoDataFrame,
    output_base_path: Path,
    file_types: Collection[config.FileTypes],
    processing_config: config.CSBprocessingConfig,
    caris_api_config: Optional[config.CarisAPIConfig],
    group_by_iho_order: bool,
) -> bool:
    """
    Exporte le GeoDataFrame vers les formats de fichiers spécifiés.

    :param data_geodataframe: GeoDataFrame à exporter.
    :type data_geodataframe: gpd.GeoDataFrame
    :param output_base_path: Chemin de base pour les fichiers de sortie.
    :type output_base_path: Path
    :param file_types: Types de fichiers à exporter.
    :type file_types: Collection[config.FileTypes]
    :param processing_config: Configuration de traitement.
    :type processing_config: config.CSBprocessingConfig
    :param caris_api_config: Configuration Caris.
    :type caris_api_config: Optional[config.CarisAPIConfig]
    :param group_by_iho_order: Regrouper par ordre IHO.
    :type group_by_iho_order: bool
    :return: True si l'exportation réussit, False sinon.
    :rtype: bool
    """
    LOGGER.info(i18n.t("converter.exporting_formats", formats=file_types))

    try:
        export.export_processed_data_to_file_types(
            data_geodataframe=data_geodataframe,
            output_base_path=output_base_path,
            file_types=file_types,
            resolution=processing_config.export.resolution,
            groub_by_iho_order=group_by_iho_order,
            config_caris=caris_api_config,
        )
        LOGGER.success(i18n.t("converter.export_success", path=output_base_path))
        return True

    except Exception as error:
        LOGGER.error(i18n.t("converter.export_error", error=error))
        return False


def convert_single_file(
    input_file: Path,
    output_path: Path,
    file_types: Collection[config.FileTypes],
    processing_config: config.CSBprocessingConfig,
    caris_api_config: Optional[config.CarisAPIConfig],
    group_by_iho_order: bool,
) -> bool:
    """
    Traite un seul fichier géospatial.

    :param input_file: Fichier d'entrée à traiter.
    :param output_path: Chemin de sortie.
    :param file_types: Types de fichiers à exporter.
    :param processing_config: Configuration de traitement.
    :param caris_api_config: Configuration Caris.
    :param group_by_iho_order: Regrouper par ordre IHO.
    :return: True si succès, False sinon.
    """
    LOGGER.info(i18n.t("converter.processing_file", file=input_file))

    data_geodataframe = read_geospatial_file(input_file)
    if data_geodataframe is None:
        LOGGER.error(i18n.t("converter.file_read_failed", file=input_file))
        return False

    # Générer le nom de fichier de base
    output_base_path = output_path / input_file.stem

    # Exporter vers les formats demandés
    return export_to_file_types(
        data_geodataframe=data_geodataframe,
        output_base_path=output_base_path,
        file_types=file_types,
        processing_config=processing_config,
        caris_api_config=caris_api_config,
        group_by_iho_order=group_by_iho_order,
    )


def convert_files_to_formats(
    input_files: Collection[Path],
    output_path: Path,
    file_types: Collection[config.FileTypes],
    config_path: Optional[Path] = CONFIG_FILE,
    group_by_iho_order: Optional[bool] = False,
) -> None:
    """
    Convertit une collection de fichiers géospatiaux (GPKG ou GeoJSON) vers différents formats.

    :param input_files: Collection de chemins des fichiers géospatiaux d'entrée.
    :type input_files: Collection[Path]
    :param output_path: Chemin du répertoire de sortie.
    :type output_path: Path
    :param file_types: Liste des formats de sortie désirés.
    :type file_types: Collection[config.FileTypes]
    :param config_path: Chemin du fichier de configuration.
    :type config_path: Optional[Path]
    :param group_by_iho_order: Regrouper les données par ordre IHO.
    :type group_by_iho_order: Optional[bool]
    """
    if not input_files:
        LOGGER.error(i18n.t("converter.no_input_files"))
        return

    files_count = len(input_files)
    if files_count == 1:
        LOGGER.info(i18n.t("converter.converting_file"))
    else:
        LOGGER.info(i18n.t("converter.converting_files", count=files_count))

    # Charger les configurations une seule fois
    processing_config, caris_api_config = load_configurations(config_path, file_types)
    if processing_config is None:
        return

    # Créer le répertoire de sortie
    output_path.mkdir(parents=True, exist_ok=True)

    successful_conversions = 0
    failed_conversions = 0

    max_workers = min(len(input_files), 4)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Soumettre toutes les tâches
        future_to_file = {
            executor.submit(
                convert_single_file,
                input_file,
                output_path,
                file_types,
                processing_config,
                caris_api_config,
                group_by_iho_order,
            ): input_file
            for input_file in input_files
        }

        # Collecter les résultats
        for future in concurrent.futures.as_completed(future_to_file):
            input_file = future_to_file[future]

            try:
                success = future.result()

                if success:
                    successful_conversions += 1
                else:
                    failed_conversions += 1

            except Exception as error:
                LOGGER.error(
                    i18n.t("converter.conversion_error", file=input_file, error=error)
                )
                failed_conversions += 1

    if failed_conversions == 0:
        if successful_conversions == 1:
            LOGGER.success(i18n.t("converter.conversion_success_single"))
        else:
            LOGGER.success(
                i18n.t(
                    "converter.conversion_success_plural", count=successful_conversions
                )
            )
    else:
        LOGGER.warning(
            i18n.t(
                "converter.conversion_partial",
                success=successful_conversions,
                failed=failed_conversions,
            )
        )
