"""
Module permettant de parser les données de type OFM.
"""

from pathlib import Path

import geopandas as gpd
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


LOGGER = logger.bind(name=f"CSB-Processing.Ingestion.Parser.{ids.OFM}")

DTYPE_DICT: dict[str, str] = {
    ids.LATITUDE_OFM: ids.FLOAT64,
    ids.LONGITUDE_OFM: ids.FLOAT64,
    ids.DEPTH_OFM: ids.FLOAT64,
}

DTYPE_DICT_SPEED: dict[str, str] = {
    schema_ids.SPEED_KN: ids.FLOAT64,
}

MANDATORY_COLUMN_EXCEPTIONS: list[ColumnException] = [
    ColumnException(column_name=ids.TIME_OFM, error=ParsingDataframeTimeError),
    ColumnException(
        column_name=ids.LONGITUDE_OFM, error=ParsingDataframeLongitudeError
    ),
    ColumnException(column_name=ids.LATITUDE_OFM, error=ParsingDataframeLatitudeError),
    ColumnException(column_name=ids.DEPTH_OFM, error=ParsingDataframeDepthError),
]


class DataParserOFM(DataParserABC):
    """
    Classe permettant de parser les données de type OFM.
    """

    def read(self, file: Path, dtype_dict: dict[str, str] = None) -> gpd.GeoDataFrame:
        """
        Méthode permettant de lire un fichier brut et retourne un geodataframe.

        :param file: Le fichier à lire.
        :type file: Path
        :param dtype_dict: Un dictionnaire de type de données.
        :type dtype_dict: dict[str, str]
        :return: Un GeoDataFrame.
        :rtype: gpd.GeoDataFrame
        """
        LOGGER.debug(
            f"Chargement d'un fichier de données brutes de type {ids.OFM} : {file}"
        )

        if dtype_dict is None:
            dtype_dict = DTYPE_DICT

        dataframe: pd.DataFrame = pd.read_csv(file)
        self.validate_columns(
            dataframe=dataframe,
            file=file,
            column_exceptions=MANDATORY_COLUMN_EXCEPTIONS,
        )
        dataframe = self.convert_dtype(
            dataframe=dataframe,
            dtype_dict=dtype_dict,
            time_column=ids.TIME_OFM,
            file=file,
        )

        LOGGER.debug(f"Conversion des données en GeoDataFrame : {file}")
        gdf: gpd.GeoDataFrame = gpd.GeoDataFrame(
            data=dataframe,
            geometry=gpd.points_from_xy(
                x=dataframe.LON, y=dataframe.LAT, crs=ids.EPSG_WGS84
            ),
        )

        gdf = self.add_speed_data_to_gdf(data=gdf, file=file.with_suffix(".csv"))

        return gdf

    def add_speed_data_to_gdf(
        self, data: gpd.GeoDataFrame, file: Path
    ) -> gpd.GeoDataFrame:
        """
        Ajoute les données de vitesse au GeoDataFrame à partir d'un fichier associé.

        :param data: Le GeoDataFrame original
        :param file: Le chemin du fichier source principal
        :return: Le GeoDataFrame avec les données de vitesse ajoutées
        """
        if not file.exists():
            LOGGER.warning(f"Le fichier de vitesse n'existe pas : {file}.")

            return data

        try:
            LOGGER.debug(f"Chargement du fichier de vitesse : {file}.")
            speed_gdf = pd.read_csv(file)

            speed_columns = [col for col in speed_gdf.columns if "Sog" in col]
            if not speed_columns:
                LOGGER.warning(
                    f"Aucune colonne contenant 'Sog' n'a été trouvée dans le fichier : {file}."
                )

                return data

            speed_column = speed_columns[0]
            LOGGER.debug(
                f"Colonne de vitesse trouvée : {speed_column} dans le fichier : {file}."
            )

            # Renommer et sélectionner uniquement les colonnes nécessaires
            speed_gdf = speed_gdf.rename(
                columns={
                    ids.TIMESTAMP_OFM: schema_ids.TIME_UTC,
                    speed_column: schema_ids.SPEED_KN,
                }
            )[[schema_ids.TIME_UTC, schema_ids.SPEED_KN]]

            # Arrondir à 3 décimales
            speed_gdf[schema_ids.SPEED_KN] = speed_gdf[schema_ids.SPEED_KN].round(3)

            # Convertir les types de données
            self.convert_dtype(
                dataframe=speed_gdf,
                dtype_dict=DTYPE_DICT_SPEED,
                time_column=schema_ids.TIME_UTC,
                file=file,
            )

            # Fusionner les données de vitesse avec le GeoDataFrame original
            return data.merge(
                speed_gdf,
                left_on=ids.TIME_OFM,
                right_on=schema_ids.TIME_UTC,
                how="left",
            ).drop(columns=schema_ids.TIME_UTC)

        except Exception as e:
            LOGGER.error(
                f"Erreur lors du chargement du fichier de vitesse : {file}. {e}"
            )

            return data

    def transform(self, data: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Méthode permettant de transformer le geodataframe pour respecter le schéma de données.

        :param data: Le geodataframe à transformer.
        :type data: gpd.GeoDataFrame
        :return: e geodataframe transformé et respectant le schéma de données DataLoggerSchema.
        :rtype: gpd.GeoDataFrame[schema_ids.DataLoggerSchema]
        """
        LOGGER.debug("Transformation du geodataframe.")

        LOGGER.debug(f"Renommage des colonnes du geodataframe.")
        data: gpd.GeoDataFrame = data.rename(
            columns={
                ids.TIME_OFM: schema_ids.TIME_UTC,
                ids.DEPTH_OFM: schema_ids.DEPTH_RAW_METER,
                ids.LONGITUDE_OFM: schema_ids.LONGITUDE_WGS84,
                ids.LATITUDE_OFM: schema_ids.LATITUDE_WGS84,
            }
        )

        return data
