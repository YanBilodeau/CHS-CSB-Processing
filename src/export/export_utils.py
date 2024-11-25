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

    :param geodataframe: (gpd.GeoDataFrame) Le GeoDataFrame.
    :param to_epsg: (int) Le code EPSG de la projection.
    """
    epsg_input: int = geodataframe.crs.to_epsg()
    if to_epsg is not None and epsg_input != to_epsg:
        LOGGER.debug(
            f"Transformation du GeoDataFrame du EPSG:{geodataframe.crs.to_epsg()} au EPSG:{to_epsg}."
        )
        geodataframe.to_crs(epsg=to_epsg, inplace=True)


def export_geodataframe_to_geojson(
    geodataframe: gpd.GeoDataFrame, output_path: Path, to_epsg: Optional[int] = WGS84
) -> None:
    """
    Sauvegarde le GeoDataFrame dans un fichier GeoJSON.

    :param geodataframe: (gpd.GeoDataFrame) Le GeoDataFrame.
    :param output_path: (Path) Le chemin du fichier de sortie.
    :param to_epsg: (int) Le code EPSG de la projection.
    """
    LOGGER.debug(f"Sauvegarde du GeoDataFrame en fichier GeoJSON : '{output_path}'.")

    transform_geodataframe_crs(geodataframe=geodataframe, to_epsg=to_epsg)
    geodataframe.to_file(
        str(sanitize_path_name(output_path)), driver="GeoJSON"
    )  # , RFC7946=True)


def export_dataframe_to_csv(dataframe: pd.DataFrame, output_path: Path) -> None:
    """
    Sauvegarde le DataFrame dans un fichier CSV.

    :param dataframe: (pd.DataFrame) Le DataFrame.
    :param output_path: (Path) Le chemin du fichier de sortie.
    """
    LOGGER.debug(f"Sauvegarde du DataFrame en fichier CSV : '{output_path}'.")

    dataframe.to_csv(sanitize_path_name(output_path), index=False)


def sanitize_path_name(path: Path) -> Path:
    """
    Fonction qui remplace les caractères invalides dans le nom d'un fichier.

    :param path: (Path) Le chemin du fichier.
    :return: (Path) Le chemin du fichier avec un nom sans caractères invalides.
    """
    LOGGER.debug(f"Validation du nom du fichier : '{path.name}'.")

    invalid_chars = r'[<>:"/\\|?*]'
    sanitized_name = re.sub(invalid_chars, "_", path.name)

    return path.with_name(sanitized_name)
