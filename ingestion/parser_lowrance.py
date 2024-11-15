from pathlib import Path
from typing import Collection

import geopandas as gpd
from loguru import logger
import pandas as pd

from .parser_abc import DataParserABC
from .parser_exception import (
    LowranceDataframeTimeError,
    LowranceDataframeLongitudeError,
    LowranceDataframeLatitudeError,
    LowranceDataframeDepthError,
)
from . import parser_ids as ids
from schema.model import DataLoggerSchema, validate_schema

LOGGER = logger.bind(name="CSB-Pipeline.Ingestion.Parser.Lowrance")

DTYPE_DICT: dict[str, str] = {
    ids.LONGITUDE_LOWRANCE: ids.FLOAT64,
    ids.LATITUDE_LOWRANCE: ids.FLOAT64,
    ids.DEPTH_LOWRANCE: ids.FLOAT64,
}


class DataParserLowrance(DataParserABC):
    @staticmethod
    def validate_columns(dataframe: pd.DataFrame, file: Path) -> None:
        """
        Méthode permettant de valider les colonnes du dataframe.

        :param dataframe: (pd.DataFrame) Le dataframe à valider.
        :param file: (Path) Le fichier source.
        :raises LowranceDataframeLongitudeError: Erreur si la colonne de longitude est absente.
        :raises LowranceDataframeLatitudeError: Erreur si la colonne de latitude est absente.
        :raises LowranceDataframeDepthError: Erreur si la colonne de profondeur est absente.
        """
        LOGGER.debug(
            f"Validation des colonnes du dataframe : {ids.LONGITUDE_LOWRANCE}, {ids.LATITUDE_LOWRANCE}, {ids.DEPTH_LOWRANCE}."
        )

        if ids.LONGITUDE_LOWRANCE not in dataframe.columns:
            raise LowranceDataframeLongitudeError(file=file)

        if ids.LATITUDE_LOWRANCE not in dataframe.columns:
            raise LowranceDataframeLatitudeError(file=file)

        if ids.DEPTH_LOWRANCE not in dataframe.columns:
            raise LowranceDataframeDepthError(file=file)

    def read(self, file: Path, dtype_dict: dict[str, str] = None) -> gpd.GeoDataFrame:
        """
        Méthode permettant de lire un fichier brut et retourne un geodataframe.

        :param file: (Path) Le fichier à lire.
        :param dtype_dict: (dict[str, str]) Un dictionnaire de type de données.
        :return: (gpd.GeoDataFrame) Un GeoDataFrame.
        """
        if dtype_dict is None:
            dtype_dict = DTYPE_DICT

        try:
            df: pd.DataFrame = pd.read_csv(
                file, dtype=dtype_dict, parse_dates=[ids.TIME_LOWRANCE]
            )

        except ValueError:
            raise LowranceDataframeTimeError(file=file)

        self.validate_columns(dataframe=df, file=file)

        gdf: gpd.GeoDataFrame = gpd.GeoDataFrame(
            data=df,
            geometry=gpd.points_from_xy(
                x=df[ids.LONGITUDE_LOWRANCE],
                y=df[ids.LATITUDE_LOWRANCE],
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
                ids.TIME_LOWRANCE: ids.TIME_UTC,
                ids.DEPTH_LOWRANCE: ids.DEPTH_METER,
                ids.LONGITUDE_LOWRANCE: ids.LONGITUDE_WGS84,
                ids.LATITUDE_LOWRANCE: ids.LATITUDE_WGS84,
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
        LOGGER.debug(
            f"Conversion des pieds en mètres de la colonne '{ids.DEPTH_METER}'."
        )
        data[ids.DEPTH_METER] = data[ids.DEPTH_METER] * 0.3048

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
