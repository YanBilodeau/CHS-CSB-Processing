from abc import ABC, abstractmethod
import concurrent.futures
from dataclasses import dataclass
from pathlib import Path
from typing import Collection
import warnings

import geopandas as gpd
from loguru import logger
import pandas as pd

from . import parser_ids as ids
from schema.model import DataLoggerSchema

LOGGER = logger.bind(name="CSB-Pipeline.Ingestion.Parser")


@dataclass
class DataParserABC(ABC):
    @staticmethod
    def convert_and_clean_dataframe(
        dataframe: pd.DataFrame, dtype_dict: dict[str, str], time_column: str
    ) -> pd.DataFrame:
        """
        Méthode permettant de convertir et nettoyer le dataframe.

        :param dataframe: (pd.DataFrame) Le dataframe à convertir.
        :param dtype_dict: (dict[str, str]) Un dictionnaire de type de données.
        :param time_column: (str) Le nom de la colonne de temps.
        :return: (pd.DataFrame) Le dataframe converti et nettoyé.
        """
        LOGGER.debug("Conversion du dtype des colonnes et nettoyage du dataframe.")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            dataframe[time_column] = pd.to_datetime(
                dataframe[time_column], errors="coerce"
            )

            for column in dtype_dict.keys():
                dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce")

        dataframe.dropna(subset=list(dtype_dict.keys()) + [time_column], inplace=True)

        return dataframe

    @staticmethod
    @abstractmethod
    def read(file: Path, **kwargs) -> gpd.GeoDataFrame:
        """
        Méthode permettant de lire un fichier brut et retourne un geodataframe.

        :param file: (Path) Le fichier à lire.
        :return: (gpd.GeoDataFrame) Un GeoDataFrame.
        """
        pass

    @abstractmethod
    def read_files(self, files: Collection[Path]) -> gpd.GeoDataFrame:
        """
        Méthode permettant de lire les fichiers brutes et retourne un geodataframe.

        :param files: (Collection[Path]) Les fichiers à lire.
        :return: (gpd.GeoDataFrame) Un GeoDataFrame.
        """
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

    @classmethod
    def from_files(cls, files: Collection[Path]) -> gpd.GeoDataFrame:
        """
        Méthode permettant de lire les fichiers brutes et retourne un geodataframe.

        :param files: (Collection[Path]) Les fichiers à lire.
        :return: (gpd.GeoDataFrame[DataLoggerSchema]) Un GeoDataFrame.
        """
        parser = cls()
        data_geodataframe: gpd.GeoDataFrame = parser.read_files(files=files)
        data_geodataframe: gpd.GeoDataFrame[DataLoggerSchema] = parser.transform(
            data=data_geodataframe
        )

        LOGGER.debug("Tri du geodataframe par datetime.")
        data_geodataframe = data_geodataframe.sort_values(by=[ids.TIME_UTC])

        LOGGER.debug("Suppression des doublons.")
        data_geodataframe = data_geodataframe.drop_duplicates(
            subset=[
                ids.TIME_UTC,
                ids.LATITUDE_WGS84,
                ids.LONGITUDE_WGS84,
                ids.DEPTH_METER,
            ]
        )

        return data_geodataframe
