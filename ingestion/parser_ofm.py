from pathlib import Path
from typing import Collection

import geopandas as gpd
from loguru import logger
import pandas as pd

from .parser_abc import DataParserABC

LOGGER = logger.bind(name="Ingestion.Parser.OFM")


class DataParserOFM(DataParserABC):
    @staticmethod
    def read(files: Collection[Path]) -> gpd.GeoDataFrame:
        """
        Méthode permettant de lire les fichiers brutes et retourne un geodataframe.

        :param files: (Collection[Path]) Les fichiers à lire.
        :return: (gpd.GeoDataFrame) Un GeoDataFrame.
        """
        LOGGER.debug(
            f"Ouverture des fichiers de données brutes OFM en geodataframe : {files}"
        )

        dtype_dict: dict[str, str] = {
            "LAT": "float64",
            "LON": "float64",
            "DEPTH": "float64",
        }

        geodataframe_list: list[gpd.GeoDataFrame] = []
        for file in files:
            df: pd.DataFrame = pd.read_csv(file, dtype=dtype_dict, parse_dates=["TIME"])
            gdf: gpd.GeoDataFrame = gpd.GeoDataFrame(
                df, geometry=gpd.points_from_xy(df.LON, df.LAT, crs="EPSG:4326")
            )
            geodataframe_list.append(gdf)

        return pd.concat(geodataframe_list)  # type: ignore

    @staticmethod
    def transform(data: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Méthode permettant de transformer le geodataframe pour respecter le schéma de données.

        :param data: (gpd.GeoDataFrame) Le geodataframe à transformer.
        :return: (gpd.GeoDataFrame) Le geodataframe transformé.
        """
        LOGGER.debug(
            "Transformation et validation du geodataframe pour respecter le schéma de données."
        )
        # todo valider schema
        return data

    @classmethod
    def from_files(cls, files: Collection[Path]) -> gpd.GeoDataFrame:
        """
        Méthode permettant de lire les fichiers brutes et retourne un geodataframe.

        :param files: (Collection[Path]) Les fichiers à lire.
        :return: (gpd.GeoDataFrame) Un GeoDataFrame.
        """
        data_geodataframe: gpd.GeoDataFrame = cls.read(files=files)

        return cls.transform(data=data_geodataframe)
