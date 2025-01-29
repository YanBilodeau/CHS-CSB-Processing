"""
Module qui contient les fonctions utilitaires pour l'exportation des données.

Ce module contient les fonctions qui permettent de sauvegarder les données dans des fichiers
de différents formats.
"""

from pathlib import Path
import re
from typing import Optional, Any

import geopandas as gpd
import pandas as pd
from loguru import logger

LOGGER = logger.bind(name="CSB-Processing.Export")
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


def transform_additional_geometry_columns_to_wkt(
    geodataframe: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """
    Transforme les colonnes de géométrie supplémentaires en WKT.

    :param geodataframe: Le GeoDataFrame.
    :type geodataframe: gpd.GeoDataFrame
    :return: Le GeoDataFrame avec les colonnes de géométrie supplémentaires transformées en WKT.
    :rtype: gpd.GeoDataFrame
    """
    additional_geometry_columns: list[str] = [
        col
        for col in geodataframe.columns
        if geodataframe[col].dtype == "geometry" and col != geodataframe.geometry.name
    ]

    if additional_geometry_columns:
        geodataframe: gpd.GeoDataFrame = geodataframe.copy()
        for col in additional_geometry_columns:
            geodataframe[col] = geodataframe[col].apply(
                lambda geom: geom.wkt if geom else None
            )

    return geodataframe


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
    geodataframe: gpd.GeoDataFrame = transform_additional_geometry_columns_to_wkt(
        geodataframe
    )

    geodataframe.to_file(str(sanitize_path_name(output_path)), driver=driver, **kwargs)


def export_geodataframe_to_geojson(
    geodataframe: gpd.GeoDataFrame,
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
    :param to_epsg: Le code EPSG de la projection.
    :type to_epsg: Optional[int]
    """
    export_geodataframe(
        geodataframe, "GeoJSON", output_path, to_epsg=to_epsg
    )  # , RFC7946=True)


def export_geodataframe_to_shapefile(
    geodataframe: gpd.GeoDataFrame,
    output_path: Path,
    to_epsg: Optional[int] = WGS84,
    **kwargs,
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
    geodataframe: gpd.GeoDataFrame,
    output_path: Path,
    to_epsg: Optional[int] = WGS84,
    **kwargs,
) -> None:
    """
    Sauvegarde le GeoDataFrame dans un fichier GeoPackage.

    :param geodataframe: Le GeoDataFrame.
    :type geodataframe: gpd.GeoDataFrame
    :param output_path: Le chemin du fichier de sortie.
    :type output_path: Path
    :param to_epsg: Le code EPSG de la projection.
    :type to_epsg: Optional[int]
    """
    export_geodataframe(geodataframe, "GPKG", output_path, to_epsg=to_epsg)


def export_geodataframe_to_csv(
    geodataframe: gpd.GeoDataFrame,
    output_path: Path,
    to_epsg: Optional[int] = WGS84,
    **kwargs,
) -> None:
    """
    Sauvegarde le GeoDataFrame dans un fichier CSV.

    :param geodataframe: Le GeoDataFrame.
    :type geodataframe: gpd.GeoDataFrame
    :param output_path: Le chemin du fichier de sortie.
    :type output_path: Path
    :param to_epsg: Le code EPSG de la projection.
    :type to_epsg: Optional[int]
    """
    LOGGER.debug(f"Sauvegarde du GeoDataFrame en fichier CSV : '{output_path}'.")

    # Transformer le système de coordonnées si nécessaire
    transform_geodataframe_crs(geodataframe, to_epsg)

    # Convertir le GeoDataFrame en DataFrame en supprimant la colonne de géométrie
    df = geodataframe.drop(columns=geodataframe.geometry.name)

    # Sauvegarder le DataFrame en CSV
    export_dataframe_to_csv(df, output_path)


def export_geodataframe_to_parquet(
    geodataframe: gpd.GeoDataFrame,
    output_path: Path,
    to_epsg: Optional[int] = WGS84,
    **kwargs: Any,
) -> None:
    """
    Sauvegarde le GeoDataFrame dans un fichier Parquet.

    :param geodataframe: Le GeoDataFrame.
    :type geodataframe: gpd.GeoDataFrame
    :param output_path: Le chemin du fichier de sortie.
    :type output_path: Path
    :param to_epsg: Le code EPSG de la projection.
    :type to_epsg: Optional[int]
    """
    LOGGER.debug(f"Sauvegarde du GeoDataFrame en fichier Parquet : '{output_path}'.")

    transform_geodataframe_crs(geodataframe, to_epsg)

    geodataframe.to_parquet(sanitize_path_name(output_path), index=False)


def export_geodataframe_to_feather(
    geodataframe: gpd.GeoDataFrame,
    output_path: Path,
    to_epsg: Optional[int] = WGS84,
    **kwargs: Any,
) -> None:
    """
    Sauvegarde le GeoDataFrame dans un fichier Feather.

    :param geodataframe: Le GeoDataFrame.
    :type geodataframe: gpd.GeoDataFrame
    :param output_path: Le chemin du fichier de sortie.
    :type output_path: Path
    :param to_epsg: Le code EPSG de la projection.
    :type to_epsg: Optional[int]
    """
    LOGGER.debug(f"Sauvegarde du GeoDataFrame en fichier Feather : '{output_path}'.")

    transform_geodataframe_crs(geodataframe, to_epsg)

    geodataframe.to_feather(sanitize_path_name(output_path))


def export_geodataframe_to_csar_api(
    geo_dataframe: gpd.GeoDataFrame, output_path: Path, config, **kwargs
) -> None:
    """
    Sauvegarde le GeoDataFrame dans un fichier CSAR.

    :param geo_dataframe: Le GeoDataFrame.
    :type geo_dataframe: gpd.GeoDataFrame
    :param output_path: Le chemin du fichier de sortie.
    :type output_path: Path
    :param config: La configuration de l'API Caris.
    :type config: CarisAPIConfigProtocol
    """
    # Importation au runtime pour éviter des problèmes de dépendances si Caris n'est pas installé
    from caris_api import export_csar_api

    LOGGER.debug(f"Sauvegarde du GeoDataFrame en fichier CSAR : '{output_path}'.")

    export_csar_api.export_geodataframe_to_csar(
        data=geo_dataframe, output_path=sanitize_path_name(output_path), config=config
    )


def export_geodataframe_to_csar_batch(
    geo_dataframe: gpd.GeoDataFrame, output_path: Path, config, **kwargs
) -> None:
    """
    Sauvegarde le GeoDataFrame dans un fichier CSAR.

    :param geo_dataframe: Le GeoDataFrame.
    :type geo_dataframe: gpd.GeoDataFrame
    :param output_path: Le chemin du fichier de sortie.
    :type output_path: Path
    :param config: La configuration de l'API Caris.
    :type config: CarisAPIConfigProtocol
    """
    from caris_api import export_csar_batch

    LOGGER.debug(f"Sauvegarde du GeoDataFrame en fichier CSAR : '{output_path}'.")

    export_csar_batch.export_geodataframe_to_csar(
        data=geo_dataframe, output_path=sanitize_path_name(output_path), config=config
    )


def export_dataframe_to_csv(
    dataframe: pd.DataFrame, output_path: Path, **kwargs
) -> None:
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
