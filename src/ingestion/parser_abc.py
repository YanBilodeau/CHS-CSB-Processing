"""
Module permettant de définir une classe abstraite pour les parsers de données.
"""

from abc import ABC, abstractmethod
import concurrent.futures
from dataclasses import dataclass
from pathlib import Path
from typing import Collection, Optional

import geopandas as gpd
from loguru import logger
import pandas as pd

from .parsing_exception import ColumnException
from .warning_capture import WarningCapture
import schema
from schema import model_ids as schema_ids

LOGGER = logger.bind(name="CSB-Processing.Ingestion.Parser.ABC")


MANDATORY_COLUNMS: list[str] = [
    schema_ids.TIME_UTC,
    schema_ids.LATITUDE_WGS84,
    schema_ids.LONGITUDE_WGS84,
    schema_ids.DEPTH_RAW_METER,
]


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

        :param dataframe: Le dataframe à valider.
        :type dataframe: pd.DataFrame
        :param file: Le fichier source.
        :type file: Path
        :param column_exceptions: Les noms et les exceptions de colonnes.
        :type column_exceptions: Collection[ColumnException]
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
        dataframe: pd.DataFrame | gpd.GeoDataFrame,
        dtype_dict: dict[str, str],
        file: Path,
        time_column: Optional[str] = None,
    ) -> pd.DataFrame | gpd.GeoDataFrame:
        """
        Méthode permettant de convertir et nettoyer le dataframe.

        :param dataframe: Le dataframe à convertir.
        :type dataframe: pd.DataFrame | gpd.GeoDataFrame
        :param dtype_dict: Un dictionnaire de type de données.
        :type dtype_dict: dict[str, str]
        :param time_column: Le nom de la colonne de temps.
        :type time_column: str | None
        :param file: Le fichier source.
        :type file: Path
        :return: Le dataframe converti et nettoyé.
        :rtype: pd.DataFrame | gpd.GeoDataFrame
        """
        LOGGER.debug(
            f"Conversion du dtype des colonnes {[column_ for column_ in dtype_dict.keys()] + [time_column] if time_column is not None else []} "
            f" du dataframe : {file}."
        )

        with WarningCapture() as warnings_list:
            if time_column is not None:
                dataframe[time_column] = pd.to_datetime(
                    dataframe[time_column], errors="coerce"
                )
                dataframe[time_column] = dataframe[time_column].astype(
                    "datetime64[ns, UTC]"
                )

            for column_ in dtype_dict.keys():
                if column_ in dataframe.columns:
                    dataframe[column_] = pd.to_numeric(
                        dataframe[column_], errors="coerce"
                    )

        if warnings_list.captured_warnings:
            LOGGER.warning(
                f"Des erreurs de conversion ont été détectées dans le fichier {file} : {warnings_list.captured_warnings}."
            )

        return dataframe

    @abstractmethod
    def read(self, file: Path, **kwargs) -> gpd.GeoDataFrame:
        """
        Méthode permettant de lire un fichier brut et retourne un geodataframe.

        :param file: Le fichier à lire.
        :type file: Path
        :return: Un GeoDataFrame.
        :rtype: gpd.GeoDataFrame
        """
        pass

    def read_files(self, files: Collection[Path]) -> gpd.GeoDataFrame:
        """
        Méthode permettant de lire les fichiers brutes et retourne un geodataframe.

        :param files: Les fichiers à lire.
        :type files: Collection[Path]
        :return: Un GeoDataFrame.
        :rtype: gpd.GeoDataFrame
        """
        LOGGER.debug(
            f"Conversion des fichiers de données brutes en geodataframe : {files}."
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

        :param data: Le geodataframe à transformer.
        :type data: gpd.GeoDataFrame
        :return: Le geodataframe transformé.
        :rtype: gpd.GeoDataFrame
        """
        pass

    @staticmethod
    def drop_na(data: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Méthode permettant de supprimer les lignes contenant des valeurs manquantes.

        :param data: Le geodataframe à nettoyer.
        :type data: gpd.GeoDataFrame
        :return: Le geodataframe nettoyé.
        :rtype: gpd.GeoDataFrame
        """
        LOGGER.debug(
            f"Suppression des valeurs manquantes sur les colonnes obligatoires : {MANDATORY_COLUNMS}."
        )

        initial_count: int = len(data)
        data = data.dropna(subset=MANDATORY_COLUNMS)
        missing_values_count: int = initial_count - len(data)

        if missing_values_count > 0:
            LOGGER.warning(
                f"{missing_values_count:,} lignes avec des valeurs manquantes ont été supprimées pour les attributs : {MANDATORY_COLUNMS}."
            )

        return data

    @staticmethod
    def remove_duplicates(data: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Méthode permettant de supprimer les doublons du geodataframe.

        :param data: Le geodataframe à nettoyer.
        :type data: gpd.GeoDataFrame
        :return: Le geodataframe nettoyé.
        :rtype: gpd.GeoDataFrame
        """
        LOGGER.debug("Suppression des doublons.")

        initial_count: int = len(data)
        data: gpd.GeoDataFrame = data.drop_duplicates(subset=MANDATORY_COLUNMS)
        duplicates_count: int = initial_count - len(data)

        if duplicates_count > 0:
            LOGGER.warning(
                f"{duplicates_count:,} doublons ont été supprimés avec les mêmes valeurs pour les attributs : {MANDATORY_COLUNMS}."
            )

        return data

    @staticmethod
    def sort_geodataframe_by_datetime(data: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Méthode permettant de trier le geodataframe par datetime.

        :param data: Le geodataframe à trier.
        :type data: gpd.GeoDataFrame
        :return: Le geodataframe trié.
        :rtype: gpd.GeoDataFrame
        """
        LOGGER.debug("Tri du geodataframe par datetime.")

        data = data.reset_index(drop=True)
        data = data.sort_values(by=[schema_ids.TIME_UTC])

        return data

    @staticmethod
    def add_empty_columns_to_geodataframe(data: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Ajoute des colonnes vides à un GeoDataFrame.

        :param data: Données brutes.
        :type data: gpd.GeoDataFrame[schema.DataLoggerSchema]
        :return: Données avec des colonnes vides.
        :rtype: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
        """
        columns: dict[str, pd.Series] = {
            schema_ids.SPEED_KN: pd.Series(dtype="float64"),
            schema_ids.DEPTH_PROCESSED_METER: pd.Series(dtype="float64"),
            schema_ids.WATER_LEVEL_INFO: pd.Series(dtype="object"),
            schema_ids.UNCERTAINTY: pd.Series(dtype="float64"),
            schema_ids.THU: pd.Series(dtype="float64"),
            schema_ids.IHO_ORDER: pd.Series(dtype="string"),
            schema_ids.OUTLIER: pd.Series(dtype="object"),
            schema_ids.WATER_LEVEL_METER: pd.Series(dtype="float64"),
            schema_ids.TIME_SERIE: pd.Series(dtype="string"),
            schema_ids.TIDE_ZONE_ID: pd.Series(dtype="string"),
            schema_ids.TIDE_ZONE_CODE: pd.Series(dtype="string"),
            schema_ids.TIDE_ZONE_NAME: pd.Series(dtype="string"),
        }

        for column_name, empty_column in columns.items():
            if column_name not in data.columns:
                LOGGER.debug(f"Ajout de la colonne {column_name} avec des valeurs nan.")

                data[column_name] = empty_column
                if empty_column.dtype == "object":  # todo valider
                    data[column_name] = data[column_name].apply(lambda _: [])

        return data

    @classmethod
    @schema.validate_schemas(
        return_schema=schema.DataLoggerWithTideZoneSchema,
    )
    def from_files(cls, files: Collection[Path]) -> gpd.GeoDataFrame:
        """
        Méthode permettant de lire les fichiers brutes et retourne un geodataframe.

        :param files: Les fichiers à lire.
        :type files: Collection[Path]
        :return: Un GeoDataFrame respectant le schéma de données DataLoggerSchema.
        :rtype: gpd.GeoDataFrame[DataLoggerWithTideZoneSchema]
        """
        parser = cls()
        data_geodataframe: gpd.GeoDataFrame = parser.read_files(files=files)
        data_geodataframe: gpd.GeoDataFrame[schema.DataLoggerSchema] = parser.transform(
            data=data_geodataframe
        )
        LOGGER.debug(f"{len(data_geodataframe):,} sondes de données brutes.")

        data_geodataframe = parser.drop_na(data=data_geodataframe)
        data_geodataframe = parser.remove_duplicates(data=data_geodataframe)
        data_geodataframe: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema] = (
            parser.add_empty_columns_to_geodataframe(data=data_geodataframe)
        )
        data_geodataframe = parser.sort_geodataframe_by_datetime(data=data_geodataframe)

        return data_geodataframe
