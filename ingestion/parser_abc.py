from abc import ABC, abstractmethod
import concurrent.futures
from dataclasses import dataclass
from pathlib import Path
from typing import Collection

import geopandas as gpd
import pandas as pd

from .schema import DataLoggerSchema


@dataclass
class DataParserABC(ABC):
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

        return data_geodataframe
