"""
Module de transformation des données de géoréférencement.

Ce module contient les fonctions de géoréférencement des données de bathymétrie.
"""

from multiprocessing import cpu_count
from typing import Optional

from cachetools import LRUCache
import dask_geopandas as dgpd
import geopandas as gpd
import numpy as np
from loguru import logger
import pandas as pd

import schema
from schema import model_ids as schema_ids

LOGGER = logger.bind(name="CSB-Pipeline.Transformation.Georeferencing")

event_dates_cache = LRUCache(maxsize=128)


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


def _validate_and_sort_data(water_level_data: dict[str, pd.DataFrame]) -> None:
    """
    Valide et trie les données de niveau d'eau.

    :param water_level_data: Niveau d'eau.
    :type water_level_data: dict[str, pd.DataFrame[schema.WaterLevelSerieDataWithMetaDataSchema]]
    """
    LOGGER.debug("Validation du schéma et tri des données de niveau d'eau.")

    for water_level_df in water_level_data.values():
        schema.validate_schema(
            data=water_level_df, schema=schema.WaterLevelSerieDataWithMetaDataSchema
        )

        LOGGER.debug(f"Dataframe {water_level_df.attrs[schema_ids.STATION_ID]} validé.")

        water_level_df.sort_values(by=schema_ids.EVENT_DATE, inplace=True)


def _get_event_dates(station_id: str, water_level_df: pd.DataFrame) -> pd.DatetimeIndex:
    """
    Récupère les dates des événements avec mise en cache.

    :param station_id: Identifiant de la station.
    :type station_id: str
    :param water_level_df: DataFrame contenant les niveaux d'eau.
    :type water_level_df: pd.DataFrame[schema.WaterLevelSerieDataWithMetaDataSchema]
    :return: Index des dates des événements.
    :rtype: pd.DatetimeIndex[pd.Timestamp]
    """
    # Mise en cache des dates des événements
    if station_id not in event_dates_cache:
        event_dates_cache[station_id] = (
            pd.to_datetime(water_level_df[schema_ids.EVENT_DATE].values)
            .tz_localize("UTC")
            .tz_convert("UTC")
        )

    return event_dates_cache[station_id]


def _interpolate_water_level(
    before_event: pd.Series,
    after_event: pd.Series,
    time_utc: pd.Timestamp,
) -> np.float64:
    """
    Interpole le niveau d'eau entre deux événements.

    :param before_event: Événement avant le temps pour lequel interpoler le niveau d'eau.
    :type before_event: pd.Series[schema.WaterLevelSerieDataSchema]
    :param after_event: Événement après le temps pour lequel interpoler le niveau d'eau.
    :type after_event: pd.Series[schema.WaterLevelSerieDataSchema]
    :param time_utc: Temps pour lequel interpoler le niveau d'eau.
    :type time_utc: pd.Timestamp
    :return: Valeur interpolée du niveau d'eau.
    :rtype: np.float64
    """
    # Interpolation linéaire
    time_diff: np.float64 = (
        after_event[schema_ids.EVENT_DATE] - before_event[schema_ids.EVENT_DATE]
    ).total_seconds()
    value_diff: float = after_event[schema_ids.VALUE] - before_event[schema_ids.VALUE]
    time_elapsed: float = (
        time_utc - before_event[schema_ids.EVENT_DATE]
    ).total_seconds()

    interpolated_value: np.float64 = before_event[schema_ids.VALUE] + (
        value_diff * (time_elapsed / time_diff)
    )

    return round(interpolated_value, 3)


def _handle_missing_data(idx_sounding: int, tide_zone_id: str) -> None:
    """
    Gère les données manquantes de niveau d'eau.

    :param idx_sounding: Index de la sonde.
    :type idx_sounding: int
    :param tide_zone_id: Identifiant de la zone de marée.
    :type tide_zone_id: str
    """
    LOGGER.warning(
        f"Aucune donnée disponible pour la zone de marée {tide_zone_id} (index {idx_sounding})."
    )

    return None


def _append_value_if_within_limit(
    event_position_wl: np.int64,
    time_utc_sounding: pd.Timestamp,
    event_dates_wl: pd.DatetimeIndex,
    water_level_df: pd.DataFrame,
    idx_sounding: int,
    tide_zone_id: str,
) -> Optional[np.float64]:
    """
    Ajoute la valeur du niveau d'eau si elle est dans les limites.

    :param event_position_wl: Position de l'événement du niveau d'eau.
    :type event_position_wl: np.int64
    :param time_utc_sounding: Temps UTC de la sonde.
    :type time_utc_sounding: pd.Timestamp
    :param event_dates_wl: Dates des événements des niveaux d'eau.
    :type event_dates_wl: pd.DatetimeIndex[pd.Timestamp]
    :param water_level_df: DataFrame contenant les niveaux d'eau.
    :type water_level_df: pd.DataFrame[schema.WaterLevelSerieDataWithMetaDataSchema]
    :param idx_sounding: Index de la sonde.
    :type idx_sounding: int
    :param tide_zone_id: Identifiant de la zone de marée.
    :type tide_zone_id: str
    :return: Valeur du niveau d'eau.
    :rtype: Optional[np.float64]
    """
    time_diff_after: float = (
        event_dates_wl[event_position_wl] - time_utc_sounding
    ).total_seconds() / 60

    if (
        time_diff_after <= 15
    ):  # todo mettre comme paramètre dans le fichier de configuration
        return water_level_df.iloc[event_position_wl][schema_ids.VALUE]

    LOGGER.warning(
        f"Pas de données de niveau d'eau suffisantes pour récupérer l'index {idx_sounding} : (tide_zone_id={tide_zone_id})."
    )

    return None


def process_row(
    row: pd.Series, water_level_data: dict[str, pd.DataFrame]
) -> Optional[np.float64]:
    """
    Traite une ligne de données de sonde.

    :param row: Ligne de données de sonde.
    :type row: pd.Series[schema.DataLoggerWithTideZoneSchema]
    :param water_level_data: Les séries temporelles des niveaux d'eau.
    :type water_level_data: dict[str, pd.DataFrame[schema.WaterLevelSerieDataWithMetaDataSchema]]
    """
    tide_zone_id: str = row.get(schema_ids.TIDE_ZONE_ID)
    time_utc_sounding: pd.Timestamp = row.get(schema_ids.TIME_UTC)
    idx_sounding: int = row.name  # type: ignore[union-attr]

    if (
        tide_zone_id not in water_level_data
        or water_level_data[tide_zone_id].empty
        or water_level_data[tide_zone_id] is None
    ):
        return _handle_missing_data(
            idx_sounding, tide_zone_id
        )  # todo tester cas limite

    water_level_df: pd.DataFrame[schema.WaterLevelSerieDataWithMetaDataSchema] = (
        water_level_data[tide_zone_id]
    )
    event_dates_wl: pd.DatetimeIndex[pd.Timestamp] = _get_event_dates(
        station_id=water_level_df.attrs[schema_ids.STATION_ID],
        water_level_df=water_level_df,
    )

    # Trouver les indices des événements avant et après
    position_after: np.int64 = event_dates_wl.searchsorted(
        time_utc_sounding, side="right"
    )
    # Vérifier si position_after est hors des limites
    if position_after >= len(event_dates_wl):
        return _append_value_if_within_limit(
            event_position_wl=np.float64(position_after - 1),
            time_utc_sounding=time_utc_sounding,
            event_dates_wl=event_dates_wl,
            water_level_df=water_level_df,
            idx_sounding=idx_sounding,
            tide_zone_id=tide_zone_id,
        )  # todo tester cas limite

    position_before: np.int64 = max(np.int64(0), np.int64(position_after - 1))
    # Vérifier si position_before est hors des limites
    if position_before < 0:
        return _append_value_if_within_limit(
            event_position_wl=position_after,
            time_utc_sounding=time_utc_sounding,
            event_dates_wl=event_dates_wl,
            water_level_df=water_level_df,
            idx_sounding=idx_sounding,
            tide_zone_id=tide_zone_id,
        )  # todo tester cas limite

    return _interpolate_water_level(
        before_event=water_level_df.iloc[position_before],
        after_event=water_level_df.iloc[position_after],
        time_utc=time_utc_sounding,
    )


@schema.validate_schemas(
    return_schema=schema.DataLoggerProcessedSchemaWithTideZone,
)
def add_water_level_to_depth_data(
    data: gpd.GeoDataFrame, water_level_data: dict[str, pd.DataFrame]
) -> gpd.GeoDataFrame:
    """
    Ajoute le niveau d'eau aux données de profondeur.

    :param data: Données brutes de profondeur.
    :type data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :param water_level_data: Niveau d'eau.
    :type water_level_data: dict[str, pd.DataFrame[schema.WaterLevelSerieDataWithMetaDataSchema]]
    :return: Données de profondeur avec le niveau d'eau.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerProcessedSchemaWithTideZone]
    """
    _validate_and_sort_data(water_level_data)

    cpu: int = cpu_count()
    LOGGER.debug(
        f"Récupération des niveaux d'eau pour les {len(data)} sonde avec {cpu} processus en parallèle."
    )

    dask_data = dgpd.from_geopandas(data, npartitions=cpu)
    interpolated_values = dask_data.map_partitions(
        lambda df: df.apply(process_row, axis=1, water_level_data=water_level_data),
        meta=("x", "f8"),
    ).compute()

    # Ajouter les valeurs interpolées à la colonne correspondante
    data[schema_ids.WATER_LEVEL_METER] = interpolated_values

    LOGGER.debug(
        f"Récupération des niveaux d'eau terminée. Il reste {data['Water_level_meter'].isna().sum()} sondes sans niveau d'eau."
    )

    return data


@schema.validate_schemas(
    data=schema.DataLoggerWithTideZoneSchema,
    return_schema=schema.DataLoggerProcessedSchema,
)
def georeference_bathymetry(
    data: gpd.GeoDataFrame, water_level: dict[str, pd.DataFrame]
) -> gpd.GeoDataFrame:  # todo prendre waterline, sensor sounder en entrée
    """
    Géoréférence les données de bathymétrie.

    :param data: Données brutes de profondeur.
    :type data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :param water_level: Niveau d'eau.
    :type water_level: dict[str, pd.DataFrame[schema.WaterLevelSerieDataWithMetaDataSchema]]
    :return: Données de profondeur avec le niveau d'eau.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerProcessedSchema]
    """
    LOGGER.debug("Géoréférencement des données bathymétrique.")

    data: gpd.GeoDataFrame[schema.DataLoggerProcessedSchemaWithTideZone] = (
        add_empty_columns_to_geodataframe(data)
    )
    data: gpd.GeoDataFrame[schema.DataLoggerProcessedSchemaWithTideZone] = (
        add_water_level_to_depth_data(data, water_level)
    )

    # todo apply georeferencing transformation

    data: gpd.GeoDataFrame[schema.DataLoggerProcessedSchema] = data.drop(
        columns=[schema_ids.TIDE_ZONE_ID]
    )

    return data
