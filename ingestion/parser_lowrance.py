from pathlib import Path
from typing import Collection

import geopandas as gpd
from loguru import logger
import pandas as pd

from .parser_abc import DataParserABC
from .parser_exception import (
    ColumnException,
    ParsingDataframeTimeError,
    ParsingDataframeLongitudeError,
    ParsingDataframeLatitudeError,
    ParsingDataframeDepthError,
)
from . import parser_ids as ids
from schema import (
    DataLoggerSchema,
    validate_schema,
    TIME_UTC,
    DEPTH_METER,
    LONGITUDE_WGS84,
    LATITUDE_WGS84,
)

LOGGER = logger.bind(name="CSB-Pipeline.Ingestion.Parser.Lowrance")

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
]


class DataParserLowrance(DataParserABC):
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
        self.validate_columns(
            dataframe=dataframe, file=file, column_exceptions=COLUMN_EXCEPTIONS
        )
        dataframe = self.convert_dtype(
            dataframe=dataframe,
            dtype_dict=dtype_dict,
            time_column=ids.TIME_LOWRANCE,
        )

        gdf: gpd.GeoDataFrame = gpd.GeoDataFrame(
            data=dataframe,
            geometry=gpd.points_from_xy(
                x=dataframe[ids.LONGITUDE_LOWRANCE],
                y=dataframe[ids.LATITUDE_LOWRANCE],
                crs=ids.EPSG_WGS84,
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
            f"Chargement des fichiers de données brutes Lowrance en geodataframe : {files}"
        )

        return super().read_files(files)

    @staticmethod
    def rename_columns(data: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Méthode permettant de renommer les colonnes du geodataframe.

        :param data: (gpd.GeoDataFrame) Le geodataframe à renommer.
        :return: (gpd.GeoDataFrame) Le geodataframe renommé.
        """
        LOGGER.debug(f"Renommage des colonnes du geodataframe.")
        data: gpd.GeoDataFrame[DataLoggerSchema] = data.rename(
            columns={
                ids.TIME_LOWRANCE: TIME_UTC,
                ids.DEPTH_LOWRANCE: DEPTH_METER,
                ids.LONGITUDE_LOWRANCE: LONGITUDE_WGS84,
                ids.LATITUDE_LOWRANCE: LATITUDE_WGS84,
            }
        )

        return data

    @staticmethod
    def remove_special_characters_from_columns(
        data: gpd.GeoDataFrame,
    ) -> gpd.GeoDataFrame:
        """
        Méthode permettant de supprimer les caractères spéciaux des noms de colonnes.

        :param data: (gpd.GeoDataFrame) Le geodataframe à transformer.
        :return: (gpd.GeoDataFrame) Le geodataframe transformé.
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

        :param data: (gpd.GeoDataFrame) Le geodataframe à transformer.
        :return: (gpd.GeoDataFrame) Le geodataframe transformé.
        """
        LOGGER.debug(f"Conversion des pieds en mètres de la colonne '{DEPTH_METER}'.")
        data[DEPTH_METER] = data[DEPTH_METER] * 0.3048

        return data

    def transform(self, data: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Méthode permettant de transformer le geodataframe pour respecter le schéma de données.

        :param data: (gpd.GeoDataFrame) Le geodataframe à transformer.
        :return: (gpd.GeoDataFrame[DataLoggerSchema]) Le geodataframe transformé.
        """
        LOGGER.debug("Transformation du geodataframe.")

        data = self.rename_columns(data)
        data = self.remove_special_characters_from_columns(data)
        data = self.convert_depth_to_meters(data)

        validate_schema(data, DataLoggerSchema)

        return data
