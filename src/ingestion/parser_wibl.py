"""
Module permettant de parser les données de type WIBL.
"""

from pathlib import Path
from typing import Any, Optional
import json

import geopandas as gpd
from loguru import logger

from .parser_abc import DataParserABC
from .parser_b12_csb import DataParserB12CSB
from . import parser_ids as ids

from .wibl.core import timestamping as ts
from .wibl.core.geojson_convert import translate


LOGGER = logger.bind(name=f"CSB-Processing.Ingestion.Parser.{ids.WIBL}")

DataWIBL = dict[str, Any]
GeoJSONWIBL = dict[str, Any]


class DataParserWIBL(DataParserABC):
    """
    Classe permettant de parser les données de type WIBL.
    """

    def __init__(self, elapsed_time_quantum: int = 1 << 32):
        """
        Initialise le parser WIBL.

        :param elapsed_time_quantum: Quantum de temps écoulé pour l'interpolation.
        """
        self.b12_csb_parser = DataParserB12CSB()
        self.elapsed_time_quantum = elapsed_time_quantum

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
            f"Chargement d'un fichier de données brutes de type {ids.WIBL} : {file}"
        )

        # Traitement fonctionnel du fichier WIBL vers GeoJSON
        output_file = process_wibl_to_geojson(file, self.elapsed_time_quantum)
        if output_file is None:
            return gpd.GeoDataFrame()

        # Utilisation du parser B12 CSB pour lire le GeoJSON
        return self.b12_csb_parser.read(file=output_file, dtype_dict=dtype_dict)

    def transform(self, data: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Méthode permettant de transformer le geodataframe pour respecter le schéma de données.

        :param data: Le geodataframe à transformer.
        :type data: gpd.GeoDataFrame
        :return: Le geodataframe transformé et respectant le schéma de données DataLoggerSchema.
        :rtype: gpd.GeoDataFrame[schema_ids.DataLoggerSchema]
        """
        return self.b12_csb_parser.transform(data=data)


def process_wibl_file(
    file: Path, elapsed_time_quantum: int = 1 << 32
) -> DataWIBL | None:
    """
    Traite un fichier WIBL et retourne les données interpolées.

    :param file: Le fichier WIBL à traiter.
    :type file: Path
    :param elapsed_time_quantum: Quantum de temps écoulé pour l'interpolation.
    :type elapsed_time_quantum: int
    :return: Les données interpolées ou None en cas d'erreur.
    :rtype: DataWIBL | None
    """
    LOGGER.debug(
        f"Traitement d'un fichier WIBL avec quantum {elapsed_time_quantum} : {file}"
    )

    try:
        return ts.time_interpolation(
            str(file),
            elapsed_time_quantum=elapsed_time_quantum,
        )
    except ts.NoTimeSource:
        LOGGER.warning(f"Aucune source de temps trouvée pour le fichier WIBL : {file}")
        return None

    except ts.NoData:
        LOGGER.warning(f"Aucune donnée trouvée dans le fichier WIBL : {file}")
        return None


def convert_to_geojson(data_dict: DataWIBL) -> GeoJSONWIBL:
    """
    Convertit les données en format GeoJSON.

    :param data_dict: Les données à convertir.
    :type data_dict: DataWIBL
    :return: Les données au format GeoJSON.
    :rtype: GeoJSONWIBL
    """
    LOGGER.debug("Conversion des données WIBL en GeoJSON")

    return translate(data_dict)


def save_geojson(geojson_dict: GeoJSONWIBL, output_file: Path) -> None:
    """
    Sauvegarde les données GeoJSON dans un fichier.

    :param geojson_dict: Les données GeoJSON à sauvegarder.
    :type geojson_dict: GeoJSONWIBL
    :param output_file: Le fichier de sortie.
    :type output_file: Path
    """
    LOGGER.debug(f"Sauvegarde du GeoJSON vers : {output_file}")

    with open(output_file, "w", encoding="utf-8") as geojson_file:
        json.dump(geojson_dict, geojson_file, indent=2, ensure_ascii=False)


def create_output_filename(input_file: Path) -> Path:
    """
    Crée le nom du fichier de sortie GeoJSON à partir du fichier d'entrée.

    :param input_file: Le fichier d'entrée.
    :type input_file: Path
    :return: Le chemin du fichier de sortie.
    :rtype: Path
    """
    return input_file.with_name(f"{input_file.stem}-{input_file.suffix[1:]}.geojson")


def process_wibl_to_geojson(
    file: Path, elapsed_time_quantum: int = 1 << 32
) -> Path | None:
    """
    Fonction de composition qui traite un fichier WIBL et le convertit en GeoJSON.

    :param file: Le fichier WIBL à traiter.
    :type file: Path
    :param elapsed_time_quantum: Quantum de temps écoulé pour l'interpolation.
    :type elapsed_time_quantum: int
    :return: Le chemin du fichier GeoJSON créé ou None en cas d'erreur.
    :rtype: Path | None
    """
    # Traitement du fichier WIBL
    data_dict: DataWIBL | None = process_wibl_file(file, elapsed_time_quantum)
    if data_dict is None:
        return None

    # Conversion en GeoJSON
    geojson_dict: GeoJSONWIBL = convert_to_geojson(data_dict)

    # Création du nom de fichier de sortie et sauvegarde
    output_file: Path = create_output_filename(file)
    save_geojson(geojson_dict, output_file)

    return output_file
