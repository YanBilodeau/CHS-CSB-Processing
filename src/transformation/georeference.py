"""
Module de transformation des données de géoréférencement.

Ce module contient les fonctions de géoréférencement des données de bathymétrie.
"""

from multiprocessing import cpu_count

from cachetools import LRUCache
import dask_geopandas as dgpd
import geopandas as gpd
import numpy as np
from loguru import logger
import pandas as pd

from .transformation_models import SensorProtocol, WaterlineProtocol
import schema
from schema import model_ids as schema_ids

LOGGER = logger.bind(name="CSB-Pipeline.Transformation.Georeferencing")

event_dates_cache = LRUCache(maxsize=128)


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

        LOGGER.debug(
            f"Dataframe des niveaux d'eau validé : {water_level_df.attrs.get(schema_ids.STATION_ID)}."
        )

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


def _handle_missing_data(idx_sounding: int, tide_zone_id: str) -> float:
    """
    Gère les données manquantes de niveau d'eau.

    :param idx_sounding: Index de la sonde.
    :type idx_sounding: int
    :param tide_zone_id: Identifiant de la zone de marée.
    :type tide_zone_id: str
    :return: np.nan
    :rtype: float
    """
    LOGGER.debug(
        f"Aucune donnée disponible pour la zone de marée {tide_zone_id} (index {idx_sounding})."
    )

    return np.nan


def _add_value_within_limit_if_applicable(
    event_position_wl: np.int64,
    time_utc_sounding: pd.Timestamp,
    event_dates_wl: pd.DatetimeIndex,
    water_level_df: pd.DataFrame,
    idx_sounding: int,
    tide_zone_id: str,
    water_level_tolerance: int | float,
) -> np.float64 | float:
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
    :param water_level_tolerance: Tolérance de temps pour la récupération de la valeur du niveau d'eau.
    :type water_level_tolerance: int | float
    :return: Valeur du niveau d'eau.
    :rtype: np.float64 | float
    """
    time_diff: float = (
        abs(event_dates_wl[event_position_wl] - time_utc_sounding).total_seconds() / 60
    )

    if time_diff <= water_level_tolerance:
        return round(water_level_df.iloc[event_position_wl][schema_ids.VALUE], 3)

    LOGGER.debug(
        f"Pas de données de niveau d'eau suffisantes pour récupérer l'index {idx_sounding} avec une "
        f"tolérance de {water_level_tolerance} minutes : (tide_zone_id={tide_zone_id})."
    )

    return np.nan


def _get_water_level_for_sounding(
    row: pd.Series,
    water_level_data: dict[str, pd.DataFrame],
    water_level_tolerance: int | float,
) -> np.float64 | float:
    """
    Récupère la valeur du niveau d'eau pour une sonde.

    :param row: Ligne de données de sonde.
    :type row: pd.Series[schema.DataLoggerWithTideZoneSchema]
    :param water_level_data: Les séries temporelles des niveaux d'eau.
    :type water_level_data: dict[str, pd.DataFrame[schema.WaterLevelSerieDataWithMetaDataSchema]]
    :param water_level_tolerance: Tolérance de temps pour la récupération de la valeur du niveau d'eau.
    :type water_level_tolerance: int | float
    :return: Valeur du niveau d'eau.
    :rtype: np.float64 | float
    """
    tide_zone_id: str = row.get(schema_ids.TIDE_ZONE_ID)
    time_utc_sounding: pd.Timestamp = row.get(schema_ids.TIME_UTC)
    idx_sounding: int = row.name  # type: ignore[union-attr]

    if (
        tide_zone_id not in water_level_data
        or water_level_data[tide_zone_id].empty
        or water_level_data[tide_zone_id] is None
    ):
        return _handle_missing_data(idx_sounding, tide_zone_id)

    water_level_df: pd.DataFrame[schema.WaterLevelSerieDataWithMetaDataSchema] = (
        water_level_data[tide_zone_id]
    )
    event_dates_wl: pd.DatetimeIndex[pd.Timestamp] = _get_event_dates(
        station_id=tide_zone_id,
        water_level_df=water_level_df,
    )

    # Trouver les indices des événements avant et après
    position_after: np.int64 = event_dates_wl.searchsorted(
        time_utc_sounding, side="right"
    )

    # Vérifier si [position_after - 1] est un match exact
    if event_dates_wl[position_after - 1] == time_utc_sounding:
        return round(
            water_level_df.iloc[position_after - 1][schema_ids.VALUE],
            3,
        )

    # Vérifier si position_after est hors des limites
    if position_after >= len(event_dates_wl):
        return _add_value_within_limit_if_applicable(
            event_position_wl=np.int64(
                position_after - 1  # -1 pour récupérer le dernier élément
            ),
            time_utc_sounding=time_utc_sounding,
            event_dates_wl=event_dates_wl,
            water_level_df=water_level_df,
            idx_sounding=idx_sounding,
            tide_zone_id=tide_zone_id,
            water_level_tolerance=water_level_tolerance,
        )

    position_before: np.int64 = np.int64(
        position_after - 1  # -1 pour récupérer l'élément avant la position_after
    )
    # Vérifier si position_before est hors des limites
    if position_before < 0:
        return _add_value_within_limit_if_applicable(
            event_position_wl=position_after,
            time_utc_sounding=time_utc_sounding,
            event_dates_wl=event_dates_wl,
            water_level_df=water_level_df,
            idx_sounding=idx_sounding,
            tide_zone_id=tide_zone_id,
            water_level_tolerance=water_level_tolerance,
        )

    return _interpolate_water_level(
        before_event=water_level_df.iloc[position_before],
        after_event=water_level_df.iloc[position_after],
        time_utc=time_utc_sounding,
    )


def get_water_levels(
    data: gpd.GeoDataFrame,
    water_level_data: dict[str, pd.DataFrame],
    water_level_tolerance: int | float,
) -> gpd.GeoDataFrame:
    """
    Ajoute le niveau d'eau aux données de profondeur.

    :param data: Données brutes de profondeur.
    :type data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :param water_level_data: Niveau d'eau.
    :type water_level_data: dict[str, pd.DataFrame[schema.WaterLevelSerieDataWithMetaDataSchema]]
    :param water_level_tolerance: Tolérance de temps pour la récupération de la valeur du niveau d'eau.
    :type water_level_tolerance: int | float
    :return: Données de profondeur avec le niveau d'eau.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    """
    _validate_and_sort_data(water_level_data)

    cpu: int = cpu_count()
    LOGGER.debug(
        f"Récupération des niveaux d'eau pour les {len(data)} sondes avec {cpu} processus en parallèle."
    )

    dask_data: dgpd.GeoDataFrame = dgpd.from_geopandas(data, npartitions=cpu)
    interpolated_values: pd.Series = dask_data.map_partitions(
        lambda df: df.apply(
            _get_water_level_for_sounding,  #  todo : weighted average ?
            axis=1,
            water_level_data=water_level_data,
            water_level_tolerance=water_level_tolerance,
        ),
        meta=("x", "f8"),
    ).compute()

    # Ajouter les valeurs interpolées à la colonne correspondante
    data[schema_ids.WATER_LEVEL_METER] = interpolated_values

    LOGGER.debug(
        f"Récupération des niveaux d'eau terminée. Il reste {data['Water_level_meter'].isna().sum()} sondes sans niveau d'eau."
    )

    return data


def apply_georeference_bathymetry(
    data: gpd.GeoDataFrame, waterline: WaterlineProtocol, sounder: SensorProtocol
) -> gpd.GeoDataFrame:
    """
    Applique la transformation de géoréférencement des données de bathymétrie.

    :param data: Données brutes de profondeur.
    :type data: gpd.GeoDataFrame[schema.DataLoggerSchema]
    :param waterline: Données de la ligne d'eau.
    :type waterline: WaterlineProtocol
    :param sounder: Données du sondeur.
    :type sounder: SensorProtocol
    :return: Données de profondeur géoréférencées.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerSchema]
    """

    def calculate_depth(row: gpd.GeoSeries) -> float:
        return (
            row[schema_ids.DEPTH_RAW_METER]
            - row[schema_ids.WATER_LEVEL_METER]
            - waterline.z
            + sounder.z  # todo valider la formule, inclure z navigation ?
        )

    cpu: int = cpu_count()

    LOGGER.debug(
        f"Application des niveaux d'eau et des bras de levier aux sondes avec {cpu} processus en parallèle."
    )

    dask_data: dgpd.GeoDataFrame = dgpd.from_geopandas(data, npartitions=cpu)

    dask_data[schema_ids.DEPTH_PROCESSED_METER] = dask_data.map_partitions(
        lambda df: df.apply(calculate_depth, axis=1),
        meta=(schema_ids.DEPTH_PROCESSED_METER, "f8"),
    )

    return dask_data.compute().pipe(gpd.GeoDataFrame)


def compute_tpu(data: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Calcule le TPU des données de bathymétrie.

    :param data: Données brut de profondeur.
    :type data: gpd.GeoDataFrame[schema.DataLoggerSchema]
    :return: Données de profondeur avec le TPU.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerSchema]
    """

    def calculate_tpu(row: gpd.GeoSeries) -> float:
        return (
            (row[schema_ids.DEPTH_PROCESSED_METER] * 0.05)
            + 2  # todo mettre en paramètre (wlo 1 ? et wlp 2 ?)  Appliquer sur depth_raw_meter ou depth_processed_meter ?
        ) or np.nan

    cpu: int = cpu_count()

    LOGGER.debug(
        f"Calcul du TPU des données de profondeur avec {cpu} processus en parallèle."
    )

    dask_data: dgpd.GeoDataFrame = dgpd.from_geopandas(data, npartitions=cpu)

    dask_data[schema_ids.UNCERTAINTY] = dask_data.map_partitions(
        lambda df: df.apply(calculate_tpu, axis=1),
        meta=(schema_ids.UNCERTAINTY, "f8"),
    )

    return dask_data.compute().pipe(gpd.GeoDataFrame)


@schema.validate_schemas(
    data=schema.DataLoggerWithTideZoneSchema,
    return_schema=schema.DataLoggerSchema,
)
def georeference_bathymetry(
    data: gpd.GeoDataFrame,
    water_level: dict[str, pd.DataFrame],
    waterline: WaterlineProtocol,
    sounder: SensorProtocol,
    water_level_tolerance: int | float = 15,
) -> gpd.GeoDataFrame:
    """
    Géoréférence les données de bathymétrie.

    :param data: Données brutes de profondeur.
    :type data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :param water_level: Niveau d'eau.
    :type water_level: dict[str, pd.DataFrame[schema.WaterLevelSerieDataWithMetaDataSchema]]
    :param waterline: Données de la ligne d'eau.
    :type waterline: WaterlineProtocol
    :param sounder: Données du sondeur.
    :type sounder: SensorProtocol
    :param water_level_tolerance: Tolérance de temps pour la récupération de la valeur du niveau d'eau.
    :type water_level_tolerance: int | float
    :return: Données de profondeur avec le niveau d'eau.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerSchema]
    """
    LOGGER.info("Géoréférencement des données bathymétrique.")

    LOGGER.info("Récupération des niveaux d'eau pour les sondes.")
    data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema] = get_water_levels(
        data, water_level, water_level_tolerance=water_level_tolerance
    )

    data: gpd.GeoDataFrame[schema.DataLoggerSchema] = data.drop(
        columns=[schema_ids.TIDE_ZONE_ID]
    )

    LOGGER.info("Application des niveaux d'eau et des bras de levier aux sondes.")
    data = apply_georeference_bathymetry(
        data=data, waterline=waterline, sounder=sounder
    )

    LOGGER.info("Calcul du TPU des données de profondeur.")
    data = compute_tpu(data)

    LOGGER.info(f"Géoréférencement des données bathymétrique terminé.")
    LOGGER.success(
        f"{data['Depth_processed_meter'].notna().sum()} sondes géoréférencées."
    )

    depth_na: np.int64 = data["Depth_processed_meter"].isna().sum()
    if depth_na > 0:
        LOGGER.warning(
            f"Il reste {depth_na} sondes sans valeur de profondeur réduite et sans valeur d'incertitude."
        )

    return data
