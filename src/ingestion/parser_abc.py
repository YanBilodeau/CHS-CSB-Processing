"""
Module permettant de définir une classe abstraite pour les parsers de données.
"""

from abc import ABC, abstractmethod
import concurrent.futures
from dataclasses import dataclass
from pathlib import Path
from typing import Collection

import geopandas as gpd
from loguru import logger
import pandas as pd

from .parser_exception import ColumnException
from .warning_capture import WarningCapture
import schema

LOGGER = logger.bind(name="CSB-Pipeline.Ingestion.Parser.ABC")


@dataclass
class DataParserABC(ABC):
    """
    Classe abstraite pour les parsers de données.
    """

    @staticmethod
    def validate_columns(
        dataframe: pd.DataFrame,
        file: Path,
        column_exceptions: Collection[ColumnException],
    ) -> None:
        """
        Méthode permettant de valider les colonnes du dataframe.

        :param dataframe: (pd.DataFrame) Le dataframe à valider.
        :param file: (Path) Le fichier source.
        :param column_exceptions: (Collection[ColumnException]) Les noms et les exceptions de colonnes.
        :raises ParsingDataframeLongitudeError: Erreur si la colonne de longitude est absente.
        :raises ParsingDataframeLatitudeError: Erreur si la colonne de latitude est absente.
        :raises ParsingDataframeDepthError: Erreur si la colonne de profondeur est absente.
        :raises ParsingDataframeTimeError: Erreur si la colonne de temps est absente.
        """
        LOGGER.debug(
            f"Validation des colonnes {[column_.column_name for column_ in column_exceptions]} du dataframe : {file}."
        )

        for column_ in column_exceptions:
            if column_.column_name not in dataframe.columns:
                raise column_.error(file=file, column=column_.column_name)  # type: ignore[arg-type]

    @staticmethod
    def convert_dtype(
        dataframe: pd.DataFrame,
        dtype_dict: dict[str, str],
        time_column: str,
        file: Path,
    ) -> pd.DataFrame:
        """
        Méthode permettant de convertir et nettoyer le dataframe.

        :param dataframe: (pd.DataFrame) Le dataframe à convertir.
        :param dtype_dict: (dict[str, str]) Un dictionnaire de type de données.
        :param time_column: (str) Le nom de la colonne de temps.
        :param file: (Path) Le fichier source.
        :return: (pd.DataFrame) Le dataframe converti et nettoyé.
        """
        LOGGER.debug(
            f"Conversion du dtype des colonnes {[column_ for column_ in dtype_dict.keys()] + [time_column]}"
            f" et suppresion des données NAN du dataframe : {file}."
        )

        with WarningCapture() as warnings_list:
            dataframe[time_column] = pd.to_datetime(
                dataframe[time_column], errors="coerce"
            )

            for column_ in dtype_dict.keys():
                dataframe[column_] = pd.to_numeric(dataframe[column_], errors="coerce")

        if warnings_list.captured_warnings:
            LOGGER.warning(
                f"Des erreurs de conversion ont été détectées dans le fichier {file} : {warnings_list.captured_warnings}."
            )

        dataframe.dropna(subset=list(dtype_dict.keys()) + [time_column], inplace=True)

        return dataframe

    @abstractmethod
    def read(self, file: Path, **kwargs) -> gpd.GeoDataFrame:
        """
        Méthode permettant de lire un fichier brut et retourne un geodataframe.

        :param file: (Path) Le fichier à lire.
        :return: (gpd.GeoDataFrame) Un GeoDataFrame.
        """
        pass

    def read_files(self, files: Collection[Path]) -> gpd.GeoDataFrame:
        """
        Méthode permettant de lire les fichiers brutes et retourne un geodataframe.

        :param files: (Collection[Path]) Les fichiers à lire.
        :return: (gpd.GeoDataFrame) Un GeoDataFrame.
        """
        LOGGER.debug(
            f"Conversion des fichiers de données brutes en geodataframe : {files}"
        )

        geodataframe_list = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.read, file) for file in files]
            for future in futures:
                geodataframe_list.append(future.result())

        return gpd.GeoDataFrame(pd.concat(geodataframe_list, ignore_index=True))

    @abstractmethod
    def transform(self, data: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Méthode permettant de transformer le geodataframe pour respecter le schéma de données.

        :param data: (gpd.GeoDataFrame) Le geodataframe à transformer.
        :return: (gpd.GeoDataFrame) Le geodataframe transformé.
        """
        pass

    @staticmethod
    def remove_duplicates(data: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Méthode permettant de supprimer les doublons du geodataframe.

        :param data: (gpd.GeoDataFrame) Le geodataframe à nettoyer.
        :return: (gpd.GeoDataFrame) Le geodataframe nettoyé.
        """
        LOGGER.debug("Suppression des doublons.")

        data = data.drop_duplicates(
            subset=[
                schema.TIME_UTC,
                schema.LATITUDE_WGS84,
                schema.LONGITUDE_WGS84,
                schema.DEPTH_METER,
            ]
        )

        return data

    @staticmethod
    def sort_geodataframe_by_datetime(data: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Méthode permettant de trier le geodataframe par datetime.

        :param data: (gpd.GeoDataFrame) Le geodataframe à trier.
        :return: (gpd.GeoDataFrame) Le geodataframe trié.
        """
        LOGGER.debug("Tri du geodataframe par datetime.")

        data = data.reset_index(drop=True)
        data = data.sort_values(by=[schema.TIME_UTC])

        return data

    @classmethod
    def from_files(cls, files: Collection[Path]) -> gpd.GeoDataFrame:
        """
        Méthode permettant de lire les fichiers brutes et retourne un geodataframe.

        :param files: (Collection[Path]) Les fichiers à lire.
        :return: (gpd.GeoDataFrame[DataLoggerSchema]) Un GeoDataFrame.
        """
        parser = cls()
        data_geodataframe: gpd.GeoDataFrame = parser.read_files(files=files)
        data_geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema] = parser.transform(
            data=data_geodataframe
        )
        data_geodataframe = parser.remove_duplicates(data=data_geodataframe)
        data_geodataframe = parser.sort_geodataframe_by_datetime(data=data_geodataframe)

        return data_geodataframe
