"""
Module qui contient la factory pour l'exportation des données.

Ce module contient la fonction export_geodataframe qui permet d'exporter un GeoDataFrame
dans un fichier du format spécifié.
"""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Callable, Any

import geopandas as gpd
from plotly.matplotlylib import Exporter

from .export_utils import (
    export_geodataframe_to_geojson,
    export_geodataframe_to_shapefile,
    export_geodataframe_to_gpkg,
    export_geodataframe_to_csar,
    export_geodataframe_to_feather,
    export_geodataframe_to_parquet,
    export_geodataframe_to_csv,
)


class FileTypes(StrEnum):
    """
    Enumération des types de fichiers de sortie.
    """

    GEOJSON: str = "geojson"
    SHAPEFILE: str = "Shapefile"
    GPKG: str = "GPKG"
    CSAR: str = "CSAR"
    PARQUET: str = "Parquet"
    FEATHER: str = "Feather"
    CSV: str = "CSV"


@dataclass(frozen=True)
class Exporter:
    """
    Classe pour l'exportation des données.

    :param extension: L'extension du fichier de sortie.
    :type extension: str
    :param function: La fonction d'exportation.
    :type function: Callable[[gpd.GeoDataFrame, Path, Any], None]
    """

    extension: str
    """Extension du fichier de sortie."""
    function: Callable[[gpd.GeoDataFrame, Path, Any], None]
    """Fonction d'exportation."""


FACTORY_EXPORT_GEODATAFRAME: dict[FileTypes, Exporter] = {
    FileTypes.GEOJSON: Exporter(
        extension=".geojson", function=export_geodataframe_to_geojson
    ),
    FileTypes.SHAPEFILE: Exporter(
        extension=".shp", function=export_geodataframe_to_shapefile
    ),
    FileTypes.GPKG: Exporter(extension=".gpkg", function=export_geodataframe_to_gpkg),
    FileTypes.CSAR: Exporter(extension=".csar", function=export_geodataframe_to_csar),
    FileTypes.PARQUET: Exporter(
        extension=".parquet", function=export_geodataframe_to_parquet
    ),
    FileTypes.FEATHER: Exporter(
        extension=".feather", function=export_geodataframe_to_feather
    ),
    FileTypes.CSV: Exporter(extension=".csv", function=export_geodataframe_to_csv),
}


def export_geodataframe(
    geodataframe: gpd.GeoDataFrame,
    file_type: FileTypes,
    output_path: Path,
    **kwargs,
) -> None:
    """
    Exporte un GeoDataFrame dans un fichier.

    :param geodataframe: Le GeoDataFrame.
    :type geodataframe: gpd.GeoDataFrame
    :param file_type: Le type de fichier de sortie.
    :type file_type: FileTypes
    :param output_path: Le chemin du fichier de sortie.
    :type output_path: Path
    """
    exporter: Exporter = FACTORY_EXPORT_GEODATAFRAME[file_type]

    exporter.function(
        geodataframe, output_path.with_suffix(exporter.extension), **kwargs
    )
