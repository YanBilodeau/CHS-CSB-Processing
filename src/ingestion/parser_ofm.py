"""
Module permettant de parser les données de type OFM.
"""

from pathlib import Path

import geopandas as gpd
from loguru import logger
import pandas as pd

from .parsing_exception import (
    ColumnException,
    ParsingDataframeTimeError,
    ParsingDataframeLongitudeError,
    ParsingDataframeLatitudeError,
    ParsingDataframeDepthError,
)
from .parser_abc import DataParserABC
from . import parser_ids as ids
import schema
from schema import model_ids as schema_ids


LOGGER = logger.bind(name="CSB-Pipeline.Ingestion.Parser.OFM")

DTYPE_DICT: dict[str, str] = {
    ids.LATITUDE_OFM: ids.FLOAT64,
    ids.LONGITUDE_OFM: ids.FLOAT64,
    ids.DEPTH_OFM: ids.FLOAT64,
}

COLUMN_EXCEPTIONS: list[ColumnException] = [
    ColumnException(column_name=ids.TIME_OFM, error=ParsingDataframeTimeError),
    ColumnException(
        column_name=ids.LONGITUDE_OFM, error=ParsingDataframeLongitudeError
    ),
    ColumnException(column_name=ids.LATITUDE_OFM, error=ParsingDataframeLatitudeError),
    ColumnException(column_name=ids.DEPTH_OFM, error=ParsingDataframeDepthError),
]


class DataParserOFM(DataParserABC):
    """
    Classe permettant de parser les données de type OFM.
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
        LOGGER.debug(f"Chargement d'un fichier de données brutes de type OFM : {file}")

        if dtype_dict is None:
            dtype_dict = DTYPE_DICT

        dataframe: pd.DataFrame = pd.read_csv(file)
        self.validate_columns(
            dataframe=dataframe, file=file, column_exceptions=COLUMN_EXCEPTIONS
        )
        dataframe = self.convert_dtype(
            dataframe=dataframe,
            dtype_dict=dtype_dict,
            time_column=ids.TIME_OFM,
            file=file,
        )

        gdf: gpd.GeoDataFrame = gpd.GeoDataFrame(
            data=dataframe,
            geometry=gpd.points_from_xy(
                x=dataframe.LON, y=dataframe.LAT, crs=ids.EPSG_WGS84
            ),
        )

        return gdf

    def transform(self, data: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Méthode permettant de transformer le geodataframe pour respecter le schéma de données.

        :param data: Le geodataframe à transformer.
        :type data: gpd.GeoDataFrame
        :return: e geodataframe transformé et respectant le schéma de données DataLoggerSchema.
        :rtype: gpd.GeoDataFrame[DataLoggerSchema]
        """
        LOGGER.debug("Transformation du geodataframe.")

        LOGGER.debug(f"Renommage des colonnes du geodataframe.")
        data: gpd.GeoDataFrame[schema.DataLoggerSchema] = data.rename(
            columns={
                ids.TIME_OFM: schema_ids.TIME_UTC,
                ids.DEPTH_OFM: schema_ids.DEPTH_METER,
                ids.LONGITUDE_OFM: schema_ids.LONGITUDE_WGS84,
                ids.LATITUDE_OFM: schema_ids.LATITUDE_WGS84,
            }
        )

        schema.validate_schema(data, schema.DataLoggerSchema)

        return data
