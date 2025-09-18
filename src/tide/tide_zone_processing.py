"""
Module pour le traitement des zones de marée et groupes temporels.

Ce module contient les fonctions pour associer les données des capteurs
aux zones de marée et créer des groupes temporels basés sur les gaps de données.
"""

from typing import Optional, Collection
import pandas as pd
import geopandas as gpd
from loguru import logger

import schema
import schema.model_ids as schema_ids
import iwls_api_request as iwls
from . import voronoi


LOGGER = logger.bind(name="CSB-Processing.TideZone")


@schema.validate_schemas(
    data_geodataframe=schema.DataLoggerWithTideZoneSchema,
    tide_zone=schema.TideZoneProtocolSchema,
    return_schema=schema.DataLoggerWithTideZoneSchema,
)
def add_tide_zone_id_to_geodataframe(
    data_geodataframe: gpd.GeoDataFrame,
    tide_zone: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """
    Récupère les zones de marées pour les données.

    :param data_geodataframe: Les données des DataLoggers.
    :type data_geodataframe: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :param tide_zone: Les zones de marées.
    :type tide_zone: gpd.GeoDataFrame[schema.TideZoneProtocolSchema]
    :return: Les données des DataLoggers avec les zones de marées.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    """
    LOGGER.debug(f"Récupération des zones de marées selon l'extension des données.")

    columns: list[str] = [
        *schema.DataLoggerSchema.__annotations__.keys(),
        *schema.DataLoggerWithVoronoiSchema.__annotations__.keys(),
    ]

    gdf_data_time_zone: gpd.GeoDataFrame[
        schema.DataLoggerWithTideZoneSchema
    ] = gpd.sjoin(
        data_geodataframe,
        tide_zone,
        how="left",
        predicate="within",
    )[
        columns
    ].rename(
        columns={
            schema_ids.ID: schema_ids.TIDE_ZONE_ID,
            schema_ids.CODE: schema_ids.TIDE_ZONE_CODE,
            schema_ids.NAME: schema_ids.TIDE_ZONE_NAME,
        }
    )

    return gdf_data_time_zone


def create_tide_zone_time_groups(
    data_geodataframe: gpd.GeoDataFrame, gap_threshold: pd.Timedelta
) -> pd.DataFrame:
    """
    Crée des groupes temporels par zone de marée en séparant les périodes avec des trous supérieurs au seuil.

    :param data_geodataframe: DataFrame avec les zones de marée et les temps UTC.
    :type data_geodataframe: gpd.GeoDataFrame
    :param gap_threshold: Seuil de temps pour définir un nouveau groupe.
    :type gap_threshold: pd.Timedelta
    :return: DataFrame avec les temps min/max par zone de marée et groupe temporel.
    :rtype: pd.DataFrame
    """
    data_sorted = data_geodataframe.sort_values(
        [schema_ids.TIDE_ZONE_ID, schema_ids.TIME_UTC]
    )
    time_diff = data_sorted.groupby(schema_ids.TIDE_ZONE_ID)[schema_ids.TIME_UTC].diff()
    new_group = (time_diff > gap_threshold) | time_diff.isna()

    data_sorted["time_group"] = new_group.groupby(
        data_sorted[schema_ids.TIDE_ZONE_ID]
    ).cumsum()

    return (
        data_sorted.groupby([schema_ids.TIDE_ZONE_ID, "time_group"])[
            schema_ids.TIME_UTC
        ]
        .agg(min_time="min", max_time="max")
        .reset_index()
        .drop(columns=["time_group"])
    )


def build_time_series_map(
    station_ids: Collection[str], tide_zone: gpd.GeoDataFrame
) -> dict[str, list[iwls.TimeSeries]]:
    """
    Construit un dictionnaire des séries temporelles pour chaque station.

    :param station_ids: Identifiants des stations.
    :type station_ids: Collection[str]
    :param tide_zone: Zones de marées contenant les informations des stations.
    :type tide_zone: gpd.GeoDataFrame
    :return: Dictionnaire des séries temporelles par station.
    :rtype: dict[str, list[iwls.TimeSeries]]
    """
    return {
        station_id: [
            iwls.TimeSeries.from_str(ts)
            for ts in voronoi.get_time_series_by_station_id(
                gdf_voronoi=tide_zone, station_id=station_id
            )
        ]
        for station_id in station_ids
    }


@schema.validate_schemas(
    data_geodataframe=schema.DataLoggerWithTideZoneSchema,
    return_schema=schema.TideZoneInfoSchema,
)
def get_intersected_tide_zone_info(
    data_geodataframe: gpd.GeoDataFrame,
    tide_zone: gpd.GeoDataFrame,
    max_gap_minutes: Optional[int] = 600,
) -> pd.DataFrame:
    """
    Récupère les zones de marées et le temps de début et de fin pour les données.

    :param data_geodataframe: Les données des DataLoggers.
    :type data_geodataframe: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :param tide_zone: Les zones de marées.
    :type tide_zone: gpd.GeoDataFrame[schema.TideZoneProtocolSchema]
    :param max_gap_minutes: Durée maximale d'un trou pour ne pas créer un nouveau groupe.
    :type max_gap_minutes: int
    :return: Les zones de marées et le temps de début et de fin pour les données.
    :rtype: pd.DataFrame[schema.TideZoneInfoSchema]
    """
    LOGGER.debug(
        f"Récupération du temps de début et de fin pour les données selon les zones de marées."
    )

    gap_threshold = pd.Timedelta(minutes=max_gap_minutes)

    tide_zone_info = create_tide_zone_time_groups(
        data_geodataframe=data_geodataframe, gap_threshold=gap_threshold
    )

    time_series_map = build_time_series_map(
        station_ids=tide_zone_info[schema_ids.TIDE_ZONE_ID].unique(),
        tide_zone=tide_zone,
    )
    tide_zone_info[schema_ids.TIME_SERIES] = tide_zone_info[
        schema_ids.TIDE_ZONE_ID
    ].map(time_series_map)

    return tide_zone_info
