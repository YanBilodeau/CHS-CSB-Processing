"""
Module qui contient les fonctions utilitaires pour l'exportation des données.

Ce module contient les fonctions qui permettent de sauvegarder les données dans des fichiers
de différents formats.
"""

from pathlib import Path
import re
from typing import Optional

import geopandas as gpd
import pandas as pd
from loguru import logger

LOGGER = logger.bind(name="CSB-Pipeline.Export")
WGS84 = 4326


def transform_geodataframe_crs(geodataframe: gpd.GeoDataFrame, to_epsg: int) -> None:
    """
    Fonction qui transforme le système de coordonnées d'un GeoDataFrame.

    :param geodataframe: Le GeoDataFrame.
    :type geodataframe: gpd.GeoDataFrame
    :param to_epsg: Le code EPSG de la projection.
    :type to_epsg: int
    """
    epsg_input: int = geodataframe.crs.to_epsg()
    if to_epsg is not None and epsg_input != to_epsg:
        LOGGER.debug(
            f"Transformation du GeoDataFrame du EPSG:{geodataframe.crs.to_epsg()} au EPSG:{to_epsg}."
        )
        geodataframe.to_crs(epsg=to_epsg, inplace=True)


def export_geodataframe(
    geodataframe: gpd.GeoDataFrame,
    driver: str,
    output_path: Path,
    to_epsg: Optional[int] = WGS84,
    **kwargs,
) -> None:
    """
    Sauvegarde le GeoDataFrame dans un fichier GeoJSON.

    :param geodataframe: Le GeoDataFrame.
    :type geodataframe: gpd.GeoDataFrame
    :param output_path: Le chemin du fichier de sortie.
    :type output_path: Path
    :param driver: Le driver du fichier de sortie.
    :type driver: str
    :param to_epsg: Le code EPSG de la projection.
    :type to_epsg: Optional[int]
    """
    LOGGER.debug(f"Sauvegarde du GeoDataFrame en fichier {driver} : '{output_path}'.")

    transform_geodataframe_crs(geodataframe=geodataframe, to_epsg=to_epsg)
    geodataframe.to_file(str(sanitize_path_name(output_path)), driver=driver, **kwargs)


def export_geodataframe_to_geojson(
    geodataframe: gpd.GeoDataFrame, output_path: Path, to_epsg: Optional[int] = WGS84
) -> None:
    """
    Sauvegarde le GeoDataFrame dans un fichier GeoJSON.

    :param geodataframe: Le GeoDataFrame.
    :type geodataframe: gpd.GeoDataFrame
    :param output_path: Le chemin du fichier de sortie.
    :type output_path: Path
    :param to_epsg: Le code EPSG de la projection.
    :type to_epsg: Optional[int]
    """
    export_geodataframe(
        geodataframe, "GeoJSON", output_path, to_epsg=to_epsg
    )  # , RFC7946=True)


def export_geodataframe_to_shapefile(
    geodataframe: gpd.GeoDataFrame, output_path: Path, to_epsg: Optional[int] = WGS84
) -> None:
    """
    Sauvegarde le GeoDataFrame dans un fichier Shapefile.

    :param geodataframe: Le GeoDataFrame.
    :type geodataframe: gpd.GeoDataFrame
    :param output_path: Le chemin du fichier de sortie.
    :type output_path: Path
    :param to_epsg: Le code EPSG de la projection.
    :type to_epsg: Optional[int]
    """
    export_geodataframe(geodataframe, "ESRI Shapefile", output_path, to_epsg=to_epsg)


def export_geodataframe_to_gpkg(
    gdf: gpd.GeoDataFrame, output_path: Path, to_epsg: Optional[int] = WGS84
) -> None:
    """
    Sauvegarde le GeoDataFrame dans un fichier GeoPackage.

    :param gdf: Le GeoDataFrame.
    :type gdf: gpd.GeoDataFrame
    :param output_path: Le chemin du fichier de sortie.
    :type output_path: Path
    :param to_epsg: Le code EPSG de la projection.
    :type to_epsg: Optional[int]
    """
    export_geodataframe(gdf, "GPKG", output_path, to_epsg=to_epsg)


def export_geodataframe_to_csv(
    gdf: gpd.GeoDataFrame, output_path: Path, to_epsg: Optional[int] = WGS84
) -> None:
    """
    Sauvegarde le GeoDataFrame dans un fichier CSV.

    :param gdf: Le GeoDataFrame.
    :type gdf: gpd.GeoDataFrame
    :param output_path: Le chemin du fichier de sortie.
    :type output_path: Path
    :param to_epsg: Le code EPSG de la projection.
    :type to_epsg: Optional[int]
    """
    export_geodataframe(gdf, "CSV", output_path, to_epsg=to_epsg)


def export_dataframe_to_csv(dataframe: pd.DataFrame, output_path: Path) -> None:
    """
    Sauvegarde le DataFrame dans un fichier CSV.

    :param dataframe: Le DataFrame.
    :type dataframe: pd.DataFrame
    :param output_path: Le chemin du fichier de sortie.
    :type output_path: Path
    """
    LOGGER.debug(f"Sauvegarde du DataFrame en fichier CSV : '{output_path}'.")

    dataframe.to_csv(sanitize_path_name(output_path), index=False)


def sanitize_path_name(path: Path) -> Path:
    """
    Fonction qui remplace les caractères invalides dans le nom d'un fichier.

    :param path: Le chemin du fichier.
    :type path: Path
    :return: Le chemin du fichier avec un nom sans caractères invalides.
    :rtype: Path
    """
    LOGGER.debug(f"Validation du nom du fichier : '{path.name}'.")

    invalid_chars = r'[<>:"/\\|?*]'
    sanitized_name = re.sub(invalid_chars, "_", path.name)

    return path.with_name(sanitized_name)
