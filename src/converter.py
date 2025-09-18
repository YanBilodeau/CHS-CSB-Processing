"""
Module de conversion des données géospatiales.

Ce module contient des fonctions pour convertir les données entre différents formats
avec validation de schéma et configuration.
"""

from pathlib import Path
from typing import Collection, Optional, Tuple

import geopandas as gpd
from loguru import logger

import config
import export
import schema
from logger.loguru_config import configure_logger


LOGGER = logger.bind(name="CSB-Processing.Converter")
configure_logger()

CONFIG_FILE: Path = Path(__file__).parent / "CONFIG_csb-processing.toml"


@schema.validate_schemas(return_schema=schema.DataLoggerSchema)
def read_gpkg_file(
    input_gpkg_path: Path, layer_name: Optional[str] = None
) -> Optional[gpd.GeoDataFrame]:
    """
    Lit un fichier GPKG et retourne un GeoDataFrame.

    :param input_gpkg_path: Chemin du fichier GPKG d'entrée.
    :type input_gpkg_path: Path
    :param layer_name: Nom de la couche à lire dans le GPKG.
    :type layer_name: Optional[str]
    :return: GeoDataFrame lu ou None en cas d'erreur.
    :rtype: Optional[gpd.GeoDataFrame[schema.DataLoggerSchema]]
    """
    if not input_gpkg_path.exists():
        LOGGER.error(f"Le fichier GPKG d'entrée n'existe pas : {input_gpkg_path}.")

        return None

    LOGGER.info(f"Lecture du fichier GPKG : {input_gpkg_path}.")

    try:
        data_geodataframe: gpd.GeoDataFrame = gpd.read_file(
            input_gpkg_path, layer=layer_name
        )
        LOGGER.success(
            f"Fichier GPKG lu avec succès : {len(data_geodataframe):,} sondes."
        )

        if data_geodataframe.empty:
            LOGGER.warning("Le fichier GPKG est vide.")

            return None

        return data_geodataframe

    except Exception as error:
        LOGGER.error(f"Erreur lors de la lecture du fichier GPKG : {error}")

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
        LOGGER.warning("Le fichier de configuration n'existe pas.")

        if config.FileTypes.CSAR in file_types:
            LOGGER.error("La configuration Caris est requise pour l'exportation CSAR.")

        return None, None

    LOGGER.info(f"Chargement de la configuration : {config_path}.")

    try:
        processing_config = config.get_data_config(config_file=config_path)
        caris_api_config = None

        # Charger la configuration Caris si nécessaire
        if not config.FileTypes.CSAR in file_types:
            return processing_config, caris_api_config

        try:
            caris_api_config = config.get_caris_api_config(config_file=config_path)

        except config.CarisConfigError as error:
            LOGGER.error(
                f"Configuration Caris requise pour l'exportation CSAR : {error}"
            )

            return None, None

        return processing_config, caris_api_config

    except Exception as error:
        LOGGER.error(f"Erreur lors du chargement de la configuration : {error}")

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
    LOGGER.info(f"Exportation vers les formats : {file_types}.")

    try:
        export.export_processed_data_to_file_types(
            data_geodataframe=data_geodataframe,
            output_base_path=output_base_path,
            file_types=file_types,
            resolution=processing_config.export.resolution,
            groub_by_iho_order=group_by_iho_order,
            config_caris=caris_api_config,
        )
        LOGGER.success(f"Conversion terminée avec succès : {output_base_path}.")

        return True

    except Exception as error:
        LOGGER.error(f"Erreur lors de l'exportation : {error}")

        return False


def convert_gpkg_to_formats(
    input_gpkg_path: Path,
    output_path: Path,
    file_types: Collection[config.FileTypes],
    config_path: Optional[Path] = CONFIG_FILE,
    group_by_iho_order: Optional[bool] = False,
) -> None:
    """
    Convertit un fichier GPKG vers différents formats avec validation de schéma.

    :param input_gpkg_path: Chemin du fichier GPKG d'entrée.
    :type input_gpkg_path: Path
    :param output_path: Chemin du répertoire de sortie.
    :type output_path: Path
    :param file_types: Liste des formats de sortie désirés.
    :type file_types: Collection[config.processing_config.FileTypes]
    :param config_path: Chemin du fichier de configuration.
    :type config_path: Optional[Path]
    :param group_by_iho_order: Regrouper les données par ordre IHO.
    :type group_by_iho_order: Optional[bool]
    """
    # Lire le fichier GPKG
    data_geodataframe = read_gpkg_file(input_gpkg_path)
    if data_geodataframe is None:
        return

    # Charger les configurations
    processing_config, caris_api_config = load_configurations(config_path, file_types)
    if processing_config is None:
        return

    # Créer le répertoire de sortie
    output_path.mkdir(parents=True, exist_ok=True)

    # Générer le nom de fichier de base
    output_base_path = output_path / input_gpkg_path.stem

    # Exporter vers les formats demandés
    export_to_file_types(
        data_geodataframe=data_geodataframe,
        output_base_path=output_base_path,
        file_types=file_types,
        processing_config=processing_config,
        caris_api_config=caris_api_config,
        group_by_iho_order=group_by_iho_order,
    )


if __name__ == "__main__":
    gpkg_path = Path(
        r"D:\Dev\CHS-CSB_Processing\Output\Data\CH-OFM-unknown-20241001-20241002.gpkg"
    )
    output_dir = Path(r"D:\Dev\CHS-CSB_Processing\Output\Converter")
    convert_gpkg_to_formats(
        input_gpkg_path=gpkg_path,
        output_path=output_dir,
        file_types=[
            config.FileTypes.CSAR
        ],
    )
