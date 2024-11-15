import concurrent.futures
from pathlib import Path
from typing import Collection

import geopandas as gpd
from loguru import logger
import pandas as pd

from .schema import DataLoggerSchema, validate_schema
from .parser_abc import DataParserABC


LOGGER = logger.bind(name="CSB-Pipeline.Ingestion.Parser.Lowrance")

DTYPE_DICT: dict[str, str] = {
    "Longitude[°WGS48]": "float64",
    "Latitude[°WGS84]": "float64",
    "WaterDepth[Feet]": "float64",
}


class DataParserBCDB(DataParserABC):
    @staticmethod
    def read(file: Path, dtype_dict: dict[str, str] = None) -> gpd.GeoDataFrame:
        """
        Méthode permettant de lire un fichier brut et retourne un geodataframe.

        :param file: (Path) Le fichier à lire.
        :param dtype_dict: (dict[str, str]) Un dictionnaire de type de données.
        :return: (gpd.GeoDataFrame) Un GeoDataFrame.
        """
        if dtype_dict is None:
            dtype_dict = DTYPE_DICT

        df: pd.DataFrame = pd.read_csv(
            file, dtype=dtype_dict, parse_dates=["DateTime[UTC]"]
        )
        gdf: gpd.GeoDataFrame = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df.LON, df.LAT, crs="EPSG:4326"),
        )

        return gdf

    def read_files(self, files: Collection[Path]) -> gpd.GeoDataFrame:
        """
        Méthode permettant de lire les fichiers brutes et retourne un geodataframe.

        :param files: (Collection[Path]) Les fichiers à lire.
        :return: (gpd.GeoDataFrame) Un GeoDataFrame.
        """
        LOGGER.debug(
            f"Ouverture des fichiers de données brutes Lowrance en geodataframe : {files}"
        )

        geodataframe_list = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.read, file, DTYPE_DICT) for file in files]
            for future in futures:
                geodataframe_list.append(future.result())

        return gpd.GeoDataFrame(pd.concat(geodataframe_list, ignore_index=True))

    def transform(self, data: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Méthode permettant de transformer le geodataframe pour respecter le schéma de données.

        :param data: (gpd.GeoDataFrame) Le geodataframe à transformer.
        :return: (gpd.GeoDataFrame[DataLoggerSchema]) Le geodataframe transformé.
        """
        LOGGER.debug(
            "Transformation et validation du geodataframe pour respecter le schéma de données."
        )

        validate_schema(data, DataLoggerSchema)

        return data
