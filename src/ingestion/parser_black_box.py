"""
Module permettant de définir un parser pour les données de type BlackBox.
"""

from pathlib import Path

import geopandas as gpd
from loguru import logger
import pandas as pd

from .parser_abc import DataParserABC
from . import parser_ids as ids
from schema import model_ids as schema_ids
from .parsing_exception import (
    ColumnException,
    ParsingDataframeTimeError,
    ParsingDataframeLongitudeError,
    ParsingDataframeLatitudeError,
    ParsingDataframeDepthError,
)

LOGGER = logger.bind(name=f"CSB-Processing.Ingestion.Parser.{ids.LOWRANCE}")


DTYPE_DICT: dict[str, str] = {
    schema_ids.DEPTH_RAW_METER: ids.FLOAT64,
    schema_ids.LATITUDE_WGS84: ids.FLOAT64,
    schema_ids.LONGITUDE_WGS84: ids.FLOAT64,
    schema_ids.SPEED_KN: ids.FLOAT64,
}

MANDATORY_COLUMN_EXCEPTIONS: list[ColumnException] = [
    ColumnException(column_name=ids.TIME_BLACKBOX, error=ParsingDataframeTimeError),
    ColumnException(column_name=ids.DATE_BLACKBOX, error=ParsingDataframeTimeError),
    ColumnException(
        column_name=schema_ids.LONGITUDE_WGS84, error=ParsingDataframeLongitudeError
    ),
    ColumnException(
        column_name=schema_ids.LATITUDE_WGS84, error=ParsingDataframeLatitudeError
    ),
    ColumnException(
        column_name=schema_ids.DEPTH_RAW_METER, error=ParsingDataframeDepthError
    ),
]


class DataParserBlackBox(DataParserABC):
    """
    Classe permettant de parser les données de type BlackBox.
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
            f"Chargement d'un fichier de données brutes de type {ids.BLACKBOX} : {file}"
        )

        if dtype_dict is None:
            dtype_dict = DTYPE_DICT

        dataframe: pd.DataFrame = pd.read_csv(
            file,
            header=None,
            names=[
                ids.TIME_BLACKBOX,
                ids.DATE_BLACKBOX,
                schema_ids.LATITUDE_WGS84,
                schema_ids.LONGITUDE_WGS84,
                ids.SPEED_BLACKBOX,
                schema_ids.DEPTH_RAW_METER,
            ],
        )
        self.validate_columns(
            dataframe=dataframe,
            file=file,
            column_exceptions=MANDATORY_COLUMN_EXCEPTIONS,
        )

        dataframe[schema_ids.TIME_UTC] = pd.to_datetime(
            dataframe[ids.DATE_BLACKBOX].astype(str).str.zfill(6)
            + " "
            + dataframe[ids.TIME_BLACKBOX].astype(str).str.zfill(8),
            format="%d%m%y %H%M%S%f",
            errors="coerce",
            utc=True,
        )

        dataframe = self.convert_dtype(
            dataframe=dataframe,
            dtype_dict=dtype_dict,
            time_column=schema_ids.TIME_UTC,
            file=file,
        )

        dataframe = dataframe.drop(columns=[ids.DATE_BLACKBOX, ids.TIME_BLACKBOX])

        LOGGER.debug(f"Conversion des données en GeoDataFrame : {file}")
        gdf: gpd.GeoDataFrame = gpd.GeoDataFrame(
            data=dataframe,
            geometry=gpd.points_from_xy(
                x=dataframe[schema_ids.LONGITUDE_WGS84],
                y=dataframe[schema_ids.LATITUDE_WGS84],
                crs=ids.EPSG_WGS84,
            ),
        )

        return gdf

    @staticmethod
    def convert_speed_to_knots(data: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Méthode permettant de convertir les vitesses en mètres par seconde en noeuds.

        :param data: Le geodataframe à transformer.
        :type data: gpd.GeoDataFrame
        :return: Le geodataframe transformé.
        :rtype: gpd.GeoDataFrame
        """
        if ids.SPEED_BLACKBOX not in data.columns:
            LOGGER.warning(
                f"La colonne '{ids.SPEED_BLACKBOX}' n'est pas présente dans le geodataframe."
            )
            return data

        LOGGER.debug(f"Conversion de la vitesse (km/h) en noeuds.")
        data[schema_ids.SPEED_KN] = round(data[ids.SPEED_BLACKBOX] * 0.539957, 3)
        data = data.drop(columns=[ids.SPEED_BLACKBOX])

        return data

    def transform(self, data: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Méthode permettant de transformer le geodataframe pour respecter le schéma de données.

        :param data: Le geodataframe à transformer.
        :type data: gpd.GeoDataFrame
        :return: Le geodataframe transformé.
        :rtype: gpd.GeoDataFrame
        """
        LOGGER.debug(f"Transformation du geodataframe.")

        data = self.convert_speed_to_knots(data)

        return data
