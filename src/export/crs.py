"""
Module pour la gestion des systèmes de coordonnées dans les GeoDataFrames.
"""

import geopandas as gpd
from loguru import logger

LOGGER = logger.bind(name="CSB-Processing.Export.CRS")


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
