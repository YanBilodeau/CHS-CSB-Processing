from pathlib import Path
from typing import Collection


import geopandas as gpd
from loguru import logger
import pandas as pd

from schema.model import DataLoggerSchema, validate_schema
from .parser_exception import (
    ColumnExceptions,
    ParsingDataframeTimeError,
    ParsingDataframeLongitudeError,
    ParsingDataframeLatitudeError,
    ParsingDataframeDepthError,
)
from .parser_abc import DataParserABC
from . import parser_ids as ids


LOGGER = logger.bind(name="CSB-Pipeline.Ingestion.Parser.DCDB")

DTYPE_DICT: dict[str, str] = {
    ids.LAT: ids.FLOAT64,
    ids.LON: ids.FLOAT64,
    ids.DEPTH: ids.FLOAT64,
}

COLUMN_EXCEPTIONS: ColumnExceptions = [
    (ids.TIME, ParsingDataframeTimeError),
    (ids.LON, ParsingDataframeLongitudeError),
    (ids.LAT, ParsingDataframeLatitudeError),
    (ids.DEPTH, ParsingDataframeDepthError),
]


class DataParserBCDB(DataParserABC):
    def read(self, file: Path, dtype_dict: dict[str, str] = None) -> gpd.GeoDataFrame:
        """
        Méthode permettant de lire un fichier brut et retourne un geodataframe.

        :param file: (Path) Le fichier à lire.
        :param dtype_dict: (dict[str, str]) Un dictionnaire de type de données.
        :return: (gpd.GeoDataFrame) Un GeoDataFrame.
        """
        if dtype_dict is None:
            dtype_dict = DTYPE_DICT

        dataframe: pd.DataFrame = pd.read_csv(file)
        self.validate_columns(dataframe=dataframe, file=file, columns=COLUMN_EXCEPTIONS)
        dataframe = self.convert_and_clean_dataframe(
            dataframe=dataframe, dtype_dict=dtype_dict, time_column=ids.TIME
        )

        gdf: gpd.GeoDataFrame = gpd.GeoDataFrame(
            data=dataframe,
            geometry=gpd.points_from_xy(
                x=dataframe.LON, y=dataframe.LAT, crs=ids.EPSG_WGS84
            ),
        )

        return gdf

    def read_files(self, files: Collection[Path]) -> gpd.GeoDataFrame:
        """
        Méthode permettant de lire les fichiers brutes et retourne un geodataframe.

        :param files: (Collection[Path]) Les fichiers à lire.
        :return: (gpd.GeoDataFrame) Un GeoDataFrame.
        """
        LOGGER.debug(
            f"Chargement des fichiers de données brutes DCDB en geodataframe : {files}"
        )

        return super().read_files(files)

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
                ids.TIME: ids.TIME_UTC,
                ids.DEPTH: ids.DEPTH_METER,
                ids.LON: ids.LONGITUDE_WGS84,
                ids.LAT: ids.LATITUDE_WGS84,
            }
        )

        validate_schema(data, DataLoggerSchema)

        return data
