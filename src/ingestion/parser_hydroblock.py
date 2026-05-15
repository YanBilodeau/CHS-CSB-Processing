"""
Module permettant de parser les données de type HydroBlock.

Le format HydroBlock est un fichier CSV délimité par des points-virgules avec l'entête :
``timestamp;latitude;longitude;chartdatumheight``

La colonne ``chartdatumheight`` représente la profondeur déjà réduite au zéro des cartes
avec l'axe positif vers le bas.
"""

from pathlib import Path

import geopandas as gpd
import i18n
from loguru import logger
import pandas as pd

from .parsing_exception import (
    ColumnException,
    ParsingDataframeTimeError,
    ParsingDataframeLongitudeError,
    ParsingDataframeLatitudeError,
    ParsingDataframeDepthError,
)
from .parser_abc import DataParserABC
from . import parser_ids as ids
from schema import model_ids as schema_ids


LOGGER = logger.bind(name=f"CSB-Processing.Ingestion.Parser.{ids.HYDROBLOCK}")

DTYPE_DICT: dict[str, str] = {
    ids.LATITUDE_HYDROBLOCK: ids.FLOAT64,
    ids.LONGITUDE_HYDROBLOCK: ids.FLOAT64,
    ids.CHARTDATUMHEIGHT_HYDROBLOCK: ids.FLOAT64,
}

MANDATORY_COLUMN_EXCEPTIONS: list[ColumnException] = [
    ColumnException(
        column_name=ids.TIMESTAMP_HYDROBLOCK, error=ParsingDataframeTimeError
    ),
    ColumnException(
        column_name=ids.LONGITUDE_HYDROBLOCK, error=ParsingDataframeLongitudeError
    ),
    ColumnException(
        column_name=ids.LATITUDE_HYDROBLOCK, error=ParsingDataframeLatitudeError
    ),
    ColumnException(
        column_name=ids.CHARTDATUMHEIGHT_HYDROBLOCK, error=ParsingDataframeDepthError
    ),
]


class DataParserHydroBlock(DataParserABC):
    """
    Classe permettant de parser les données de type HydroBlock.

    Le fichier HydroBlock est un CSV délimité par des points-virgules contenant les colonnes :
    ``timestamp``, ``latitude``, ``longitude``, ``chartdatumheight``.

    La profondeur (``chartdatumheight``) est déjà réduite au zéro des cartes,
    axe positif vers le bas.
    """

    def read(self, file: Path, dtype_dict: dict[str, str] = None) -> gpd.GeoDataFrame:
        """
        Méthode permettant de lire un fichier brut HydroBlock et retourne un GeoDataFrame.

        :param file: Le fichier à lire.
        :type file: Path
        :param dtype_dict: Un dictionnaire de type de données.
        :type dtype_dict: dict[str, str]
        :return: Un GeoDataFrame.
        :rtype: gpd.GeoDataFrame
        """
        LOGGER.debug(
            i18n.t(
                "ingestion.parser_shared.loading_file", type=ids.HYDROBLOCK, file=file
            )
        )

        if dtype_dict is None:
            dtype_dict = DTYPE_DICT

        dataframe: pd.DataFrame = pd.read_csv(file, sep=";")
        self.validate_columns(
            dataframe=dataframe,
            file=file,
            column_exceptions=MANDATORY_COLUMN_EXCEPTIONS,
        )
        dataframe = self.convert_dtype(
            dataframe=dataframe,
            dtype_dict=dtype_dict,
            time_column=ids.TIMESTAMP_HYDROBLOCK,
            file=file,
        )

        LOGGER.debug(
            i18n.t("ingestion.parser_shared.converting_to_geodataframe", file=file)
        )
        gdf: gpd.GeoDataFrame = gpd.GeoDataFrame(
            data=dataframe,
            geometry=gpd.points_from_xy(
                x=dataframe[ids.LONGITUDE_HYDROBLOCK],
                y=dataframe[ids.LATITUDE_HYDROBLOCK],
                crs=ids.EPSG_WGS84,
            ),
        )

        return gdf

    def transform(self, data: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Méthode permettant de transformer le GeoDataFrame pour respecter le schéma de données.

        Les colonnes sont renommées pour correspondre au schéma ``DataLoggerSchema``.
        La colonne ``chartdatumheight`` (profondeur au zéro des cartes, axe positif vers le bas)
        est directement mappée vers ``DEPTH_RAW_METER`` sans transformation.

        :param data: Le GeoDataFrame à transformer.
        :type data: gpd.GeoDataFrame
        :return: Le GeoDataFrame transformé respectant le schéma ``DataLoggerSchema``.
        :rtype: gpd.GeoDataFrame[schema.DataLoggerSchema]
        """
        LOGGER.debug(i18n.t("ingestion.parser_shared.transforming_geodataframe"))

        LOGGER.debug(i18n.t("ingestion.parser_shared.renaming_columns"))
        data: gpd.GeoDataFrame = data.rename(
            columns={
                ids.TIMESTAMP_HYDROBLOCK: schema_ids.TIME_UTC,
                ids.CHARTDATUMHEIGHT_HYDROBLOCK: schema_ids.DEPTH_RAW_METER,
                ids.LONGITUDE_HYDROBLOCK: schema_ids.LONGITUDE_WGS84,
                ids.LATITUDE_HYDROBLOCK: schema_ids.LATITUDE_WGS84,
            }
        )

        return data
