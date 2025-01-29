"""
Module pour exporter un Geodataframe vers un fichier CSAR avec l'API de Caris.

Ce module contient les fonctions nécessaires pour exporter un Geodataframe vers un fichier CSAR avec l'API de Caris.
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Optional

import geopandas as gpd
from loguru import logger

from .import_caris_module import CarisModuleImporter, CarisConfigProtocol
import schema
from schema import model_ids as schema_ids


coverage: Optional[ModuleType] = None

LOGGER = logger.bind(name="CSB-Processing.Caris.API.ExportCSAR")

NDV: int = -9999
COSYS: str = """
        GEOGCS["WGS 84",
        DATUM["World Geodetic System 1984",
            SPHEROID["WGS 84",6378137,298.2572235629972,
                AUTHORITY["EPSG","7030"]],
            TOWGS84[0,0,0,0,0,0,0],
            AUTHORITY["EPSG","6326"]],
        PRIMEM["Greenwich",0,
            AUTHORITY["EPSG","8901"]],
        UNIT["degree (supplier to define representation)",0.0174532925199433,
            AUTHORITY["EPSG","9122"]],
        EXTENSION["tx_authority","WG84"],
        AUTHORITY["EPSG","4326"]]
        """

POSITION: str = "Position"
DEPTH_RAW: str = "Depth_raw"
DEPTH: str = "Depth"
WATER_LEVEL: str = "Water_level"
UNCERTAINTY: str = "Uncertainty"


def _get_band_info() -> dict[str, coverage.BandInfo]:
    """
    Crée un dictionnaire de bandes pour le fichier CSAR.

    :return: Un dictionnaire de bandes.
    :rtype: dict[str, coverage.Band]
    """
    LOGGER.debug("Création des bandes du fichier CSAR.")

    return {
        POSITION: coverage.BandInfo(
            type=coverage.DataType.FLOAT64,
            tuple_length=2,
            name=POSITION,
            direction=coverage.Direction.NAP,
            units="",
            category=coverage.Category.SCALAR,
            ndv=(NDV, NDV),
        ),
        DEPTH_RAW: coverage.BandInfo(
            type=coverage.DataType.FLOAT32,
            tuple_length=1,
            name=DEPTH_RAW,
            direction=coverage.Direction.DEPTH,
            units="m",
            category=coverage.Category.SCALAR,
            ndv=NDV,
        ),
        DEPTH: coverage.BandInfo(
            type=coverage.DataType.FLOAT32,
            tuple_length=1,
            name=DEPTH,
            direction=coverage.Direction.DEPTH,
            units="m",
            category=coverage.Category.SCALAR,
            ndv=NDV,
        ),
        WATER_LEVEL: coverage.BandInfo(
            type=coverage.DataType.FLOAT32,
            tuple_length=1,
            name=WATER_LEVEL,
            direction=coverage.Direction.DEPTH,
            units="m",
            category=coverage.Category.SCALAR,
            ndv=NDV,
        ),
        UNCERTAINTY: coverage.BandInfo(
            type=coverage.DataType.FLOAT32,
            tuple_length=1,
            name=UNCERTAINTY,
            direction=coverage.Direction.NAP,
            units="m",
            category=coverage.Category.SCALAR,
            ndv=NDV,
        ),
    }


def _get_band_options(
    band_info: dict[str, coverage.BandInfo],
    extent: tuple[tuple[float]] = ((0.0, 0.0), (-180.0, 90.0)),
    cosys: str = COSYS,
) -> coverage.Options:
    """
    Crée les options pour le fichier CSAR.

    :param band_info: Les informations des bandes.
    :type band_info: dict[str, coverage.BandInfo]
    :param extent: Les limites de la couverture.
    :type extent: tuple[tuple[float]]
    :param cosys: Le système de coordonnées.
    :type cosys: str
    :return: Les options pour le fichier CSAR.
    :rtype: coverage.Options
    """
    LOGGER.debug("Création des options des bandes du fichier CSAR.")

    options = coverage.Options()
    options.open_type = coverage.OpenType.WRITE
    options.position_band_name = POSITION
    options.band_info = band_info
    options.extents = extent
    options.wkt_cosys = cosys

    return options


def _get_value_blocks(data: gpd.GeoDataFrame) -> list[dict[str, list]]:
    """
    Prépare les blocks de données à partir du Geodataframe.

    :param data: Le Geodataframe contenat les données.
    :type data: gpd.GeoDataFrame[schema.DataLoggerSchema]
    :return: Les blocks de données.
    :rtype: list[dict[str, list]]
    """
    LOGGER.debug(f"Préparation des blocks de données à partir du Geodataframe.")

    return [
        {
            POSITION: list(
                zip(
                    data[schema_ids.LONGITUDE_WGS84],
                    data[schema_ids.LATITUDE_WGS84],
                )
            ),
            DEPTH_RAW: data[schema_ids.DEPTH_RAW_METER].tolist(),
            DEPTH: data[schema_ids.DEPTH_PROCESSED_METER].tolist(),
            WATER_LEVEL: data[schema_ids.WATER_LEVEL_METER].tolist(),
            UNCERTAINTY: data[schema_ids.UNCERTAINTY].tolist(),
        }
    ]


def _create_bounding_polygon(csar_file_path: Path) -> None:
    """
    Crée le polygone de délimitation du fichier CSAR.

    :param csar_file_path: Le chemin du fichier CSAR.
    :type csar_file_path: Path
    """
    LOGGER.debug(
        f"Création du polygone de délimitation du fichier CSAR : {csar_file_path}."
    )

    csar_file: coverage.Cloud = coverage.Cloud(
        filename=str(csar_file_path),
        options=coverage.Options(open_type=coverage.OpenType.WRITE),
    )
    csar_file.bounding_polygon = coverage.generate_polygon(csar_file)


def ensure_directory_exists(directory: Path) -> None:
    """
    Assure que le répertoire existe.

    :param directory: Le répertoire.
    :type directory: Path
    """
    LOGGER.debug(f"Validation que le répertoire existe : {directory}.")

    if not directory.exists():
        directory.mkdir(parents=True)


def remove_existing_files(files: list[Path]) -> None:
    """
    Supprime les fichiers existants.

    :param files: Les fichiers à supprimer.
    :type files: list[Path]
    """
    for file in files:
        if file.exists():
            LOGGER.debug(f"Suppression du fichier existant : {file}.")
            file.unlink()


@schema.validate_schemas(data=schema.DataLoggerSchema)
def export_geodataframe_to_csar(
    data: gpd.GeoDataFrame, output_path: Path, config: CarisConfigProtocol
) -> None:
    """
    Exporte un Geodataframe vers un fichier CSAR.

    :param data: Le Geodataframe à exporter.
    :type data: gpd.GeoDataFrame[schema.DataLoggerSchema]
    :param output_path: Le chemin du fichier de sortie.
    :type output_path: Path
    :param config: La configuration de l'API Caris.
    :type config: CarisConfigProtocol
    """
    global coverage

    caris_wrapper: CarisModuleImporter = CarisModuleImporter(config=config)
    coverage = caris_wrapper.coverage

    ensure_directory_exists(output_path.parent)

    band_info: dict[str, coverage.BandInfo] = _get_band_info()
    opts: coverage.Options = _get_band_options(band_info=band_info)
    blocks: list[dict[str, list]] | None = _get_value_blocks(data=data)

    if not blocks:
        LOGGER.warning(f"Aucune donnée à exporter en CSAR.")
        return

    opts.iterator = lambda: iter(blocks)

    remove_existing_files(files=[output_path, output_path.with_suffix(".csar0")])
    try:
        coverage.Cloud(filename=str(output_path), options=opts)
        _create_bounding_polygon(csar_file_path=output_path)

    except Exception as error:
        LOGGER.error(
            f"Erreur lors de la création du fichier de séparation {output_path.name}: {error}"
        )
