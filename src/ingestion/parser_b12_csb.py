"""
Module permettant de parser les données de type B12_CSB.
"""

from pathlib import Path

import geopandas as gpd
from loguru import logger

from .parser_abc import DataParserABC
from . import parser_ids as ids
from schema import model_ids as schema_ids
from .parsing_exception import (
    ColumnException,
    ParsingDataframeTimeError,
    ParsingDataframeDepthError,
)


LOGGER = logger.bind(name=f"CSB-Processing.Ingestion.Parser.{ids.B12_CSB}")


DTYPE_DICT: dict[str, str] = {
    ids.DEPTH_B12_CSB: ids.FLOAT64,
    schema_ids.LONGITUDE_WGS84: ids.FLOAT64,
    schema_ids.LATITUDE_WGS84: ids.FLOAT64,
}

MANDATORY_COLUMN_EXCEPTIONS: list[ColumnException] = [
    ColumnException(column_name=ids.TIME_B12_CSB, error=ParsingDataframeTimeError),
    ColumnException(column_name=ids.DEPTH_B12_CSB, error=ParsingDataframeDepthError),
]


class DataParserB12CSB(DataParserABC):
    """
    Classe permettant de parser les données de type B12-CSB.
    """

    def read(self, file: Path, dtype_dict: dict[str, str] = None) -> gpd.GeoDataFrame:
        """
        Méthode permettant de lire un fichier brut et retourne un geodataframe.

        :param file: Le fichier à lire.
        :type file: Path
        :param dtype_dict: Un dictionnaire de type de données.
        :type dtype_dict: dict[str, str]
        :return: Un GeoDataFrame.
        :rtype: gpd.GeoDataFrame
        """
        LOGGER.debug(
            f"Chargement d'un fichier de données brutes de type {ids.B12_CSB} : {file}"
        )

        if dtype_dict is None:
            dtype_dict = DTYPE_DICT

        gdf: gpd.GeoDataFrame = gpd.read_file(file)

        self.validate_columns(
            dataframe=gdf,
            file=file,
            column_exceptions=MANDATORY_COLUMN_EXCEPTIONS,
        )

        gdf[schema_ids.LONGITUDE_WGS84] = gdf.geometry.x
        gdf[schema_ids.LATITUDE_WGS84] = gdf.geometry.y

        gdf = self.convert_dtype(
            dataframe=gdf,
            dtype_dict=dtype_dict,
            time_column=ids.TIME_B12_CSB,
            file=file,
        )

        return gdf

    def transform(self, data: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Méthode permettant de transformer le geodataframe pour respecter le schéma de données.

        :param data: Le geodataframe à transformer.
        :type data: gpd.GeoDataFrame
        :return: Le geodataframe transformé et respectant le schéma de données DataLoggerSchema.
        :rtype: gpd.GeoDataFrame[schema_ids.DataLoggerSchema]
        """
        LOGGER.debug("Transformation du geodataframe.")

        LOGGER.debug(f"Renommage des colonnes du geodataframe.")
        data: gpd.GeoDataFrame = data.rename(
            columns={
                ids.TIME_B12_CSB: schema_ids.TIME_UTC,
                ids.DEPTH_B12_CSB: schema_ids.DEPTH_RAW_METER,
            }
        )

        return data
