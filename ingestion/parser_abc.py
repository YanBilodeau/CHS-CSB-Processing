from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Collection

import geopandas as gpd


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
        pass

    @abstractmethod
    def transform(self, data: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Méthode permettant de transformer le geodataframe pour respecter le schéma de données.

        :param data: (gpd.GeoDataFrame) Le geodataframe à transformer.
        :return: (gpd.GeoDataFrame) Le geodataframe transformé.
        """
        pass

    @classmethod
    @abstractmethod
    def from_files(cls, files: Collection[Path]) -> gpd.GeoDataFrame:
        """
        Méthode permettant de lire les fichiers brutes et retourne un geodataframe.

        :param files: (Collection[Path]) Les fichiers à lire.
        :return: (gpd.GeoDataFrame) Un GeoDataFrame transformé respectant le schéma de données.
        """
        pass
