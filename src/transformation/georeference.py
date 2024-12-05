"""
Module de transformation des données de géoréférencement.

Ce module contient les fonctions pour géoréférencer les données des DataLoggers.
"""

import geopandas as gpd
from loguru import logger
import pandas as pd

import schema
from schema import model_ids as schema_ids

LOGGER = logger.bind(name="CSB-Pipeline.Transformation.Georeferencing")


def add_empty_columns_to_geodataframe(data: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Ajoute des colonnes vides à un GeoDataFrame.

    :param data: Données brutes.
    :type data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :return: Données avec des colonnes vides.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerProcessedSchemaWithTideZone]
    """
    columns: dict[str, pd.Series] = {
        schema_ids.DEPTH_PROCESSED_METER: pd.Series(dtype="float64"),
        schema_ids.WATER_LEVEL_METER: pd.Series(dtype="float64"),
        schema_ids.UNCERTAINTY: pd.Series(dtype="float64"),
    }

    LOGGER.debug(f"Ajout de colonnes vides aux données : {columns.keys()}.")

    for column_name, empty_column in columns.items():
        data[column_name] = empty_column

    return data


@schema.validate_schemas(
    return_schema=schema.DataLoggerProcessedSchemaWithTideZone,
)
def add_water_level_to_depth_data(
    data: gpd.GeoDataFrame, water_level: dict[str, pd.DataFrame]
) -> gpd.GeoDataFrame:
    """
    Ajoute le niveau d'eau aux données de profondeur.

    :param data: Données brutes de profondeur.
    :type data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :param water_level: Niveau d'eau.
    :type water_level: dict[str, pd.DataFrame[schema.WaterLevelSerieDataWithMetaDataSchema]]
    :return: Données de profondeur avec le niveau d'eau.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerProcessedSchemaWithTideZone]
    """
    pass


@schema.validate_schemas(
    data=schema.DataLoggerWithTideZoneSchema
)  # todo add return schema
def georeference_bathymetry(
    data: gpd.GeoDataFrame, water_level: dict[str, pd.DataFrame]
) -> gpd.GeoDataFrame:
    """
    Géoréférence les données de bathymétrie.

    :param data: Données brutes de profondeur.
    :type data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :param water_level: Niveau d'eau.
    :type water_level: dict[str, pd.DataFrame[schema.WaterLevelSerieDataWithMetaDataSchema]]
    :return: Données de profondeur avec le niveau d'eau.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerProcessedSchema]
    """
    data: gpd.GeoDataFrame[schema.DataLoggerProcessedSchemaWithTideZone] = (
        add_empty_columns_to_geodataframe(data)
    )
    # data: gpd.GeoDataFrame[schema.DataLoggerProcessedSchemaWithTideZone] = (
    #     add_water_level_to_depth_data(data, water_level)
    # )

    return data
