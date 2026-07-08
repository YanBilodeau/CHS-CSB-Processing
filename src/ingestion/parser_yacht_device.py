"""
Module permettant de parser les données de type Yacht Device.
"""

from pathlib import Path

import geopandas as gpd
import i18n
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
from schema import model_ids as schema_ids


LOGGER = logger.bind(name=f"CSB-Processing.Ingestion.Parser.{ids.YACHT_DEVICE}")

DTYPE_DICT: dict[str, str] = {
    ids.LATITUDE_YACHT_DEVICE: ids.FLOAT64,
    ids.LONGITUDE_YACHT_DEVICE: ids.FLOAT64,
    ids.DEPTH_YACHT_DEVICE: ids.FLOAT64,
    ids.SOG_YACHT_DEVICE: ids.FLOAT64,
}

MANDATORY_COLUMN_EXCEPTIONS: list[ColumnException] = [
    ColumnException(column_name=ids.TIME_YACHT_DEVICE, error=ParsingDataframeTimeError),
    ColumnException(
        column_name=ids.LONGITUDE_YACHT_DEVICE, error=ParsingDataframeLongitudeError
    ),
    ColumnException(
        column_name=ids.LATITUDE_YACHT_DEVICE, error=ParsingDataframeLatitudeError
    ),
    ColumnException(
        column_name=ids.DEPTH_YACHT_DEVICE, error=ParsingDataframeDepthError
    ),
]


class DataParserYachtDevice(DataParserABC):
    """
    Classe permettant de parser les données de type Yacht Device.
    """

    def read(
        self, file: Path, dtype_dict: dict[str, str] | None = None
    ) -> gpd.GeoDataFrame:
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
            i18n.t(
                "ingestion.parser_shared.loading_file", type=ids.YACHT_DEVICE, file=file
            )
        )

        if dtype_dict is None:
            dtype_dict = DTYPE_DICT

        dataframe: pd.DataFrame = pd.read_csv(file, sep=";")
        self.validate_columns(
            dataframe=dataframe,
            file=file,
            column_exceptions=MANDATORY_COLUMN_EXCEPTIONS,
        )
        dataframe = self.convert_dtype(
            dataframe=dataframe,
            dtype_dict=dtype_dict,
            time_column=ids.TIME_YACHT_DEVICE,
            file=file,
            time_format="%Y-%m-%d %H:%M:%S",
        )

        LOGGER.debug(
            i18n.t("ingestion.parser_shared.converting_to_geodataframe", file=file)
        )
        gdf: gpd.GeoDataFrame = gpd.GeoDataFrame(
            data=dataframe,
            geometry=gpd.points_from_xy(
                x=dataframe[ids.LONGITUDE_YACHT_DEVICE],
                y=dataframe[ids.LATITUDE_YACHT_DEVICE],
                crs=ids.EPSG_WGS84,
            ),
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
        LOGGER.debug(i18n.t("ingestion.parser_shared.transforming_geodataframe"))

        LOGGER.debug(i18n.t("ingestion.parser_shared.renaming_columns"))
        data: gpd.GeoDataFrame = data.rename(
            columns={
                ids.TIME_YACHT_DEVICE: schema_ids.TIME_UTC,
                ids.DEPTH_YACHT_DEVICE: schema_ids.DEPTH_RAW_METER,
                ids.LONGITUDE_YACHT_DEVICE: schema_ids.LONGITUDE_WGS84,
                ids.LATITUDE_YACHT_DEVICE: schema_ids.LATITUDE_WGS84,
                ids.SOG_YACHT_DEVICE: schema_ids.SPEED_KN,
            }
        )

        return data
