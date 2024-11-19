from pathlib import Path

import geopandas as gpd
from loguru import logger
import pandas as pd

from .parser_exception import (
    ColumnException,
    ParsingDataframeTimeError,
    ParsingDataframeLongitudeError,
    ParsingDataframeLatitudeError,
    ParsingDataframeDepthError,
)
from .parser_abc import DataParserABC
from . import parser_ids as ids
from schema import (
    DataLoggerSchema,
    validate_schema,
    TIME_UTC,
    DEPTH_METER,
    LONGITUDE_WGS84,
    LATITUDE_WGS84,
)


LOGGER = logger.bind(name="CSB-Pipeline.Ingestion.Parser.DCDB")

DTYPE_DICT: dict[str, str] = {
    ids.LATITUDE_DCDB: ids.FLOAT64,
    ids.LONGITUDE_DCDB: ids.FLOAT64,
    ids.DEPTH_DCDB: ids.FLOAT64,
}

COLUMN_EXCEPTIONS: list[ColumnException] = [
    ColumnException(column_name=ids.TIME, error=ParsingDataframeTimeError),
    ColumnException(column_name=ids.LONGITUDE_DCDB, error=ParsingDataframeLongitudeError),
    ColumnException(column_name=ids.LATITUDE_DCDB, error=ParsingDataframeLatitudeError),
    ColumnException(column_name=ids.DEPTH_DCDB, error=ParsingDataframeDepthError),
]


class DataParserBCDB(DataParserABC):
    def read(self, file: Path, dtype_dict: dict[str, str] = None) -> gpd.GeoDataFrame:
        """
        Méthode permettant de lire un fichier brut et retourne un geodataframe.

        :param file: (Path) Le fichier à lire.
        :param dtype_dict: (dict[str, str]) Un dictionnaire de type de données.
        :return: (gpd.GeoDataFrame) Un GeoDataFrame.
        """
        LOGGER.debug(f"Chargement d'un fichier de données brutes de type DCDB : {file}")

        if dtype_dict is None:
            dtype_dict = DTYPE_DICT

        dataframe: pd.DataFrame = pd.read_csv(file)
        self.validate_columns(
            dataframe=dataframe, file=file, column_exceptions=COLUMN_EXCEPTIONS
        )
        dataframe = self.convert_dtype(
            dataframe=dataframe, dtype_dict=dtype_dict, time_column=ids.TIME, file=file
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

        :param data: (gpd.GeoDataFrame) Le geodataframe à transformer.
        :return: (gpd.GeoDataFrame[DataLoggerSchema]) Le geodataframe transformé.
        """
        LOGGER.debug("Transformation du geodataframe.")

        LOGGER.debug(f"Renommage des colonnes du geodataframe.")
        data: gpd.GeoDataFrame[DataLoggerSchema] = data.rename(
            columns={
                ids.TIME: TIME_UTC,
                ids.DEPTH_DCDB: DEPTH_METER,
                ids.LONGITUDE_DCDB: LONGITUDE_WGS84,
                ids.LATITUDE_DCDB: LATITUDE_WGS84,
            }
        )

        validate_schema(data, DataLoggerSchema)

        return data
