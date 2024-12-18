"""
Module permettant de définir un parser pour les données de type Lowrance.
"""

from pathlib import Path

import geopandas as gpd
from loguru import logger
import pandas as pd

from .parser_abc import DataParserABC
from .parsing_exception import (
    ColumnException,
    ParsingDataframeTimeError,
    ParsingDataframeLongitudeError,
    ParsingDataframeLatitudeError,
    ParsingDataframeDepthError,
    ParsingError,
)
from . import parser_ids as ids
import schema
from schema import model_ids as schema_ids

LOGGER = logger.bind(name="CSB-Processing.Ingestion.Parser.Lowrance")

DTYPE_DICT: dict[str, str] = {
    ids.LONGITUDE_LOWRANCE: ids.FLOAT64,
    ids.LATITUDE_LOWRANCE: ids.FLOAT64,
    ids.DEPTH_LOWRANCE: ids.FLOAT64,
}

COLUMN_EXCEPTIONS: list[ColumnException] = [
    ColumnException(column_name=ids.TIME_LOWRANCE, error=ParsingDataframeTimeError),
    ColumnException(
        column_name=ids.LONGITUDE_LOWRANCE, error=ParsingDataframeLongitudeError
    ),
    ColumnException(
        column_name=ids.LATITUDE_LOWRANCE, error=ParsingDataframeLatitudeError
    ),
    ColumnException(column_name=ids.DEPTH_LOWRANCE, error=ParsingDataframeDepthError),
    ColumnException(column_name=ids.SURVEY_TYPE_LOWRANCE, error=ParsingError),
]


class DataParserLowrance(DataParserABC):
    """
    Classe permettant de parser les données de type Lowrance.
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
            f"Chargement du fichier de données brutes de type Lowrance : {file}"
        )

        dtype_dict = dtype_dict or DTYPE_DICT

        dataframe: pd.DataFrame = pd.read_csv(file)
        self.validate_columns(
            dataframe=dataframe, file=file, column_exceptions=COLUMN_EXCEPTIONS
        )
        dataframe = self.convert_dtype(
            dataframe=dataframe,
            dtype_dict=dtype_dict,
            time_column=ids.TIME_LOWRANCE,
            file=file,
        )
        # Arrondir les timestamps pour uniformiser la précision
        dataframe[ids.TIME_LOWRANCE] = dataframe[ids.TIME_LOWRANCE].dt.round("100ms")
        dataframe = dataframe.query(
            f"{ids.SURVEY_TYPE_LOWRANCE} == '{ids.PRIMARY_LOWRANCE}'"
        )

        LOGGER.debug(f"Conversion des données en GeoDataFrame : {file}")
        gdf: gpd.GeoDataFrame = gpd.GeoDataFrame(
            data=dataframe,
            geometry=gpd.points_from_xy(
                x=dataframe[ids.LONGITUDE_LOWRANCE],
                y=dataframe[ids.LATITUDE_LOWRANCE],
                crs=ids.EPSG_WGS84,
            ),
        )

        return gdf

    @staticmethod
    def rename_columns(data: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Méthode permettant de renommer les colonnes du geodataframe.

        :param data: Le geodataframe à renommer.
        :type data: gpd.GeoDataFrame
        :return: Le geodataframe renommé.
        :rtype: gpd.GeoDataFrame
        """
        LOGGER.debug(f"Renommage des colonnes du geodataframe.")
        data: gpd.GeoDataFrame[schema.DataLoggerSchema] = data.rename(
            columns={
                ids.TIME_LOWRANCE: schema_ids.TIME_UTC,
                ids.DEPTH_LOWRANCE: schema_ids.DEPTH_RAW_METER,
                ids.LONGITUDE_LOWRANCE: schema_ids.LONGITUDE_WGS84,
                ids.LATITUDE_LOWRANCE: schema_ids.LATITUDE_WGS84,
            }
        )

        return data

    @staticmethod
    def remove_special_characters_from_columns(
        data: gpd.GeoDataFrame,
    ) -> gpd.GeoDataFrame:
        """
        Méthode permettant de supprimer les caractères spéciaux des noms de colonnes.

        :param data: Le geodataframe à transformer.
        :type data: gpd.GeoDataFrame
        :return: Le geodataframe transformé.
        :rtype: gpd.GeoDataFrame
        """
        LOGGER.debug("Suppression des caractères spéciaux des noms de colonnes.")
        data.columns = (
            data.columns.str.replace("[", "_")
            .str.replace("]", "")
            .str.replace("/", "-")
        )

        return data

    @staticmethod
    def convert_depth_to_meters(data: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Méthode permettant de convertir les profondeurs en mètres.

        :param data: Le geodataframe à transformer.
        :type data: gpd.GeoDataFrame
        :return: Le geodataframe transformé.
        :rtype: gpd.GeoDataFrame
        """
        LOGGER.debug(
            f"Conversion des pieds en mètres de la colonne '{schema_ids.DEPTH_RAW_METER}'."
        )
        data[schema_ids.DEPTH_RAW_METER] = round(
            data[schema_ids.DEPTH_RAW_METER] * 0.3048, 3
        )

        return data

    def transform(self, data: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Méthode permettant de transformer le geodataframe pour respecter le schéma de données.

        :param data: Le geodataframe à transformer.
        :type data: gpd.GeoDataFrame
        :return: Le geodataframe transformé respectant le schéma de données DataLoggerSchema.
        :rtype: gpd.GeoDataFrame[schema.DataLoggerSchema]
        """
        LOGGER.debug("Transformation du geodataframe.")

        data = self.rename_columns(data)
        data = self.remove_special_characters_from_columns(data)
        data = self.convert_depth_to_meters(data)

        return data
