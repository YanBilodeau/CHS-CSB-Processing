import geopandas as gpd
from loguru import logger

from schema.model import DataLoggerSchema

LOGGER = logger.bind(name="CSB-Pipeline.Transformation.DataCleaning")


def clean_depth(geodataframe: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Fonction qui nettoie les données de profondeur.

    :param geodataframe: (gpd.GeoDataFrame[DataLoggerSchema]) Le GeoDataFrame.
    :return: (gpd.GeoDataFrame[DataLoggerSchema]) Le GeoDataFrame nettoyé.
    """
    LOGGER.debug("Nettoyage des données de profondeur.")

    geodataframe: gpd.GeoDataFrame[DataLoggerSchema] = geodataframe[
        geodataframe["Depth_meter"].notna() & (geodataframe["Depth_meter"] > 0)
    ]

    return geodataframe
