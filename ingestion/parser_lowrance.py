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
from .schema import DataLoggerSchema, validate_schema

LOGGER = logger.bind(name="CSB-Pipeline.Ingestion.Parser.Lowrance")

DTYPE_DICT: dict[str, str] = {
    ids.LONGITUDE_LOWRANCE: ids.FLOAT64,
    ids.LATITUDE_LOWRANCE: ids.FLOAT64,
    ids.DEPTH_LOWRANCE: ids.FLOAT64,
}


class DataParserLowrance(DataParserABC):
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

        try:
            df: pd.DataFrame = pd.read_csv(
                file, dtype=dtype_dict, parse_dates=[ids.TIME_LOWRANCE]
            )

        except ValueError:
            raise LowranceDataframeTimeError(file=file)

        if ids.LONGITUDE_LOWRANCE not in df.columns:
            raise LowranceDataframeLongitudeError(file=file)

        if ids.LATITUDE_LOWRANCE not in df.columns:
            raise LowranceDataframeLatitudeError(file=file)

        if ids.DEPTH_LOWRANCE not in df.columns:
            raise LowranceDataframeDepthError(file=file)

        gdf: gpd.GeoDataFrame = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(
                df[ids.LONGITUDE_LOWRANCE],
                df[ids.LATITUDE_LOWRANCE],
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
            f"Ouverture des fichiers de données brutes Lowrance en geodataframe : {files}"
        )

        return super().read_files(files)

    def transform(self, data: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Méthode permettant de transformer le geodataframe pour respecter le schéma de données.

        :param data: (gpd.GeoDataFrame) Le geodataframe à transformer.
        :return: (gpd.GeoDataFrame[DataLoggerSchema]) Le geodataframe transformé.
        """
        LOGGER.debug(
            "Transformation et validation du geodataframe pour respecter le schéma de données."
        )

        # valider si UTC, WGS84 et Feet sinon levé une exception

        data = data.rename(
            columns={
                ids.TIME_LOWRANCE: ids.TIME,
                ids.DEPTH_LOWRANCE: ids.DEPTH,
                ids.LONGITUDE_LOWRANCE: ids.LON,
                ids.LATITUDE_LOWRANCE: ids.LAT,
            }
        )

        print(data.columns)

        # tranformer feet to meters

        validate_schema(data, DataLoggerSchema)

        return data
