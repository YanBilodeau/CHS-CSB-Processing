"""
Module de transformation des données de géoréférencement.

Ce module contient les fonctions de géoréférencement des données de bathymétrie.
"""

from multiprocessing import cpu_count

from cachetools import LRUCache
import geopandas as gpd
import numpy as np
from loguru import logger
import pandas as pd
from typing import Optional

from .exception_tranformation import WaterLevelDataRequiredError
from . import order
from .transformation_models import SensorProtocol, WaterlineProtocol
from . import uncertainty
import schema
from schema import model_ids as schema_ids

LOGGER = logger.bind(name="CSB-Processing.Transformation.Georeferencing")

event_dates_cache = LRUCache(maxsize=128)

CPU_COUNT: int = cpu_count()


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
    cache_key: str = (
        f"{station_id}-{water_level_df.attrs[schema_ids.START_TIME]}"
        f"-{water_level_df.attrs[schema_ids.END_TIME]}-{len(water_level_df)}"
    )

    # Mise en cache des dates des événements
    if cache_key not in event_dates_cache:
        event_dates = pd.to_datetime(water_level_df[schema_ids.EVENT_DATE].values)

        if event_dates.tz is None:
            event_dates = event_dates.tz_localize("UTC")

        event_dates_cache[cache_key] = event_dates

    return event_dates_cache[cache_key]


def get_water_levels_vectorized(
    data: gpd.GeoDataFrame,
    water_level_data: dict[str, pd.DataFrame],
    water_level_tolerance: pd.Timedelta,
) -> gpd.GeoDataFrame:
    """
    Ajoute le niveau d'eau aux données de profondeur de manière vectorisée.

    :param data: Données brutes de profondeur.
    :type data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :param water_level_data: Niveau d'eau.
    :type water_level_data: dict[str, pd.DataFrame[schema.WaterLevelSerieDataWithMetaDataSchema]]
    :param water_level_tolerance: Tolérance de temps pour la récupération de la valeur du niveau d'eau.
    :type water_level_tolerance: pd.Timedelta
    :return: Données de profondeur avec le niveau d'eau.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    """
    _validate_and_sort_data(water_level_data)

    LOGGER.debug(f"Récupération des niveaux d'eau pour les {len(data)} sondes.")

    # Initialiser les colonnes de résultat directement dans le DataFrame original
    data.loc[:, schema_ids.WATER_LEVEL_METER] = np.nan
    data.loc[:, schema_ids.TIME_SERIE] = None

    # Grouper par tide_zone_id pour traitement vectorisé
    for tide_zone_id, zone_group in data.groupby(schema_ids.TIDE_ZONE_ID):
        if tide_zone_id not in water_level_data or water_level_data[tide_zone_id].empty:
            continue

        water_level_df = water_level_data[tide_zone_id]
        event_dates_wl = _get_event_dates(tide_zone_id, water_level_df)

        # Vectoriser la recherche de positions
        time_utc_values = zone_group[schema_ids.TIME_UTC]
        positions_after = event_dates_wl.searchsorted(time_utc_values, side="right")

        # Calculer les masques pour différents cas
        exact_match_mask = np.zeros(len(positions_after), dtype=bool)
        valid_positions = (positions_after > 0) & (
            positions_after <= len(event_dates_wl)
        )

        for i, pos in enumerate(positions_after):
            if 0 < pos <= len(event_dates_wl):
                if event_dates_wl[pos - 1] == time_utc_values.iloc[i]:
                    exact_match_mask[i] = True  # todo: vectoriser ?

        # Traiter les correspondances exactes
        exact_indices = zone_group.index[exact_match_mask]
        exact_positions = positions_after[exact_match_mask] - 1

        if len(exact_indices) > 0:
            data.loc[exact_indices, schema_ids.WATER_LEVEL_METER] = (
                water_level_df.iloc[exact_positions][schema_ids.VALUE].round(3).values
            )
            data.loc[exact_indices, schema_ids.TIME_SERIE] = water_level_df.iloc[
                exact_positions
            ][schema_ids.TIME_SERIE_CODE].values

        # Traiter les cas nécessitants interpolation/tolérance
        non_exact_mask = ~exact_match_mask & valid_positions
        if non_exact_mask.any():
            _process_non_exact_matches(
                data,
                zone_group,
                non_exact_mask,
                positions_after,
                water_level_df,
                event_dates_wl,
                time_utc_values,
                water_level_tolerance,
            )

    LOGGER.debug(
        f"Récupération des niveaux d'eau terminée. Il reste {data[schema_ids.WATER_LEVEL_METER].isna().sum()} sondes sans niveau d'eau."
    )

    return data


def _handle_out_of_bounds_after(
    gdf: gpd.GeoDataFrame,
    indices_to_process: pd.Index,
    times_to_process: pd.Series,
    positions_to_process: np.ndarray,
    event_dates_wl: pd.DatetimeIndex,
    water_level_df: pd.DataFrame,
    tolerance_seconds: float,
) -> None:
    """
    Cas où la position après est hors limites: on peut utiliser le dernier point si dans la tolérance.

    :param gdf: GeoDataFrame des données de profondeur.
    :type gdf: gpd.GeoDataFrame[schema.DataLoggerWithTideZone
    :param indices_to_process: Indices des lignes à traiter.
    :type indices_to_process: pd.Index
    :param times_to_process: Séries temporelles des lignes à traiter.
    :type times_to_process: pd.Series[pd.Timestamp]
    :param positions_to_process: Positions après dans les données de niveau d'eau.
    :type positions_to_process: np.ndarray
    :param event_dates_wl: Dates des événements de niveau d'eau.
    :type event_dates_wl: pd.DatetimeIndex[pd.Timestamp]
    :param water_level_df: DataFrame des niveaux d'eau.
    :type water_level_df: pd.DataFrame[schema.WaterLevelSerieDataWithMetaDataSchema]
    :param tolerance_seconds: Tolérance en secondes pour la récupération du niveau d'eau.
    :type tolerance_seconds: float
    """
    out_of_bounds_after = positions_to_process >= len(event_dates_wl)
    if not out_of_bounds_after.any():
        return

    max_event_idx = len(event_dates_wl) - 1
    last_event_time = event_dates_wl[max_event_idx]
    time_diffs_last = np.abs(
        (times_to_process[out_of_bounds_after] - last_event_time).dt.total_seconds()
    )
    within_tolerance = time_diffs_last <= tolerance_seconds
    if not within_tolerance.any():
        return

    valid_indices = indices_to_process[out_of_bounds_after][within_tolerance]
    gdf.loc[valid_indices, schema_ids.WATER_LEVEL_METER] = round(
        water_level_df.iloc[max_event_idx][schema_ids.VALUE], 3
    )
    gdf.loc[valid_indices, schema_ids.TIME_SERIE] = water_level_df.iloc[max_event_idx][
        schema_ids.TIME_SERIE_CODE
    ]


def _handle_out_of_bounds_before(
    gdf: gpd.GeoDataFrame,
    indices_to_process: pd.Index,
    times_to_process: pd.Series,
    positions_before: np.ndarray,
    event_dates_wl: pd.DatetimeIndex,
    water_level_df: pd.DataFrame,
    tolerance_seconds: float,
) -> None:
    """
    Cas où la position avant est hors limites: on peut utiliser le premier point si dans la tolérance.

    :param gdf: GeoDataFrame des données de profondeur.
    :type gdf: gpd.GeoDataFrame[schema.DataLoggerWithTideZone
    :param indices_to_process: Indices des lignes à traiter.
    :type indices_to_process: pd.Index
    :param times_to_process: Séries temporelles des lignes à traiter.
    :type times_to_process: pd.Series[pd.Timestamp]
    :param positions_before: Positions avant dans les données de niveau d'eau.
    :type positions_before: np.ndarray
    :param event_dates_wl: Dates des événements de niveau d'eau.
    :type event_dates_wl: pd.DatetimeIndex[pd.Timestamp]
    :param water_level_df: DataFrame des niveaux d'eau.
    :type water_level_df: pd.DataFrame[schema.WaterLevelSerieDataWithMetaDataSchema]
    :param tolerance_seconds: Tolérance en secondes pour la récupération du niveau d'eau.
    :type tolerance_seconds: float
    """
    out_of_bounds_before = positions_before < 0
    if not out_of_bounds_before.any():
        return

    first_event_time = event_dates_wl[0]
    time_diffs_first = np.abs(
        (times_to_process[out_of_bounds_before] - first_event_time).dt.total_seconds()
    )
    within_tolerance = time_diffs_first <= tolerance_seconds
    if not within_tolerance.any():
        return

    valid_indices = indices_to_process[out_of_bounds_before][within_tolerance]
    gdf.loc[valid_indices, schema_ids.WATER_LEVEL_METER] = round(
        water_level_df.iloc[0][schema_ids.VALUE], 3
    )
    gdf.loc[valid_indices, schema_ids.TIME_SERIE] = water_level_df.iloc[0][
        schema_ids.TIME_SERIE_CODE
    ]


def _handle_interpolation(
    gdf: gpd.GeoDataFrame,
    indices_to_process: pd.Index,
    positions_before: np.ndarray,
    positions_to_process: np.ndarray,
    times_to_process: pd.Series,
    event_dates_wl: pd.DatetimeIndex,
    water_level_df: pd.DataFrame,
    tolerance_seconds: float,
) -> None:
    """
    Cas d'interpolation linéaire entre deux points consécutifs si dans la tolérance.

    :param gdf: GeoDataFrame des données de profondeur.
    :type gdf: gpd.GeoDataFrame[schema.DataLoggerWithTideZone
    :param indices_to_process: Indices des lignes à traiter.
    :type indices_to_process: pd.Index
    :param positions_before: Positions avant dans les données de niveau d'eau.
    :type positions_before: np.ndarray
    :param positions_to_process: Positions après dans les données de niveau d'eau.
    :type positions_to_process: np.ndarray
    :param times_to_process: Séries temporelles des lignes à traiter.
    :type times_to_process: pd.Series[pd.Timestamp]
    :param event_dates_wl: Dates des événements de niveau d'eau.
    :type event_dates_wl: pd.DatetimeIndex[pd.Timestamp]
    :param water_level_df: DataFrame des niveaux d'eau.
    :type water_level_df: pd.DataFrame[schema.WaterLevelSerieDataWithMetaDataSchema]
    :param tolerance_seconds: Tolérance en secondes pour la récupération du niveau d'eau.
    :type tolerance_seconds: float
    """
    max_len = len(event_dates_wl)
    out_of_bounds_after = positions_to_process >= max_len
    out_of_bounds_before = positions_before < 0
    valid_interpolation = ~out_of_bounds_after & ~out_of_bounds_before
    if not valid_interpolation.any():
        return

    interp_indices = indices_to_process[valid_interpolation]
    interp_pos_before = positions_before[valid_interpolation]
    interp_pos_after = positions_to_process[valid_interpolation]
    interp_times = times_to_process[valid_interpolation]

    before_events = water_level_df.iloc[interp_pos_before]
    after_events = water_level_df.iloc[interp_pos_after]

    time_diffs_event = (
        (
            after_events[schema_ids.EVENT_DATE].values
            - before_events[schema_ids.EVENT_DATE].values
        )
        .astype("timedelta64[s]")
        .astype(float)
    )

    # Exiger que l'intervalle total soit <= 2 * tolérance
    tolerance_mask = time_diffs_event <= (2 * tolerance_seconds)
    if not tolerance_mask.any():
        return

    final_indices = interp_indices[tolerance_mask]
    final_before = before_events[tolerance_mask]
    final_after = after_events[tolerance_mask]
    final_times = interp_times[tolerance_mask]
    final_time_diffs = time_diffs_event[tolerance_mask]

    value_diffs = (
        final_after[schema_ids.VALUE].values - final_before[schema_ids.VALUE].values
    )
    time_elapsed = (
        (final_times.values - final_before[schema_ids.EVENT_DATE].values)
        .astype("timedelta64[s]")
        .astype(float)
    )

    interpolated_values = final_before[schema_ids.VALUE].values + (
        value_diffs * (time_elapsed / final_time_diffs)
    )

    gdf.loc[final_indices, schema_ids.WATER_LEVEL_METER] = np.round(
        interpolated_values, 3
    )
    gdf.loc[final_indices, schema_ids.TIME_SERIE] = [
        f"LinearInterpolation[{after} - {before}]"
        for after, before in zip(
            final_after[schema_ids.TIME_SERIE_CODE].values,
            final_before[schema_ids.TIME_SERIE_CODE].values,
        )
    ]


def _process_non_exact_matches(
    gdf: gpd.GeoDataFrame,
    zone_group: pd.DataFrame,
    mask: np.ndarray,
    positions_after: np.ndarray,
    water_level_df: pd.DataFrame,
    event_dates_wl: pd.DatetimeIndex,
    time_utc_values: pd.Series,
    water_level_tolerance: pd.Timedelta,
) -> None:
    """
    Orchestration des traitements des cas non-exacts (hors limites & interpolation).

    :param gdf: GeoDataFrame des données de profondeur.
    :type gdf: gpd.GeoDataFrame[schema.DataLoggerWithTideZone
    :param zone_group: Groupe de données pour une zone de marée spécifique.
    :type zone_group: pd.DataFrame[schema.DataLoggerWithTideZoneSchema]
    :param mask: Masque des lignes à traiter.
    :type mask: np.ndarray
    :param positions_after: Positions après dans les données de niveau d'eau.
    :type positions_after: np.ndarray
    :param water_level_df: DataFrame des niveaux d'eau.
    :type water_level_df: pd.DataFrame[schema.WaterLevelSerieDataWithMetaDataSchema]
    :param event_dates_wl: Dates des événements de niveau d'eau.
    :type event_dates_wl: pd.DatetimeIndex[pd.Timestamp]
    :param time_utc_values: Séries temporelles des lignes à traiter.
    :type time_utc_values: pd.Series[pd.Timestamp]
    :param water_level_tolerance: Tolérance en temps pour la récupération de la valeur du niveau d'eau.
    :type water_level_tolerance: pd.Timedelta
    """
    if not mask.any():
        return

    indices_to_process = zone_group.index[mask]
    positions_to_process = positions_after[mask]
    times_to_process = time_utc_values[mask]
    positions_before = positions_to_process - 1
    tolerance_seconds = water_level_tolerance.total_seconds()

    _handle_out_of_bounds_after(
        gdf=gdf,
        indices_to_process=indices_to_process,
        times_to_process=times_to_process,
        positions_to_process=positions_to_process,
        event_dates_wl=event_dates_wl,
        water_level_df=water_level_df,
        tolerance_seconds=tolerance_seconds,
    )

    _handle_out_of_bounds_before(
        gdf=gdf,
        indices_to_process=indices_to_process,
        times_to_process=times_to_process,
        positions_before=positions_before,
        event_dates_wl=event_dates_wl,
        water_level_df=water_level_df,
        tolerance_seconds=tolerance_seconds,
    )

    _handle_interpolation(
        gdf=gdf,
        indices_to_process=indices_to_process,
        positions_before=positions_before,
        positions_to_process=positions_to_process,
        times_to_process=times_to_process,
        event_dates_wl=event_dates_wl,
        water_level_df=water_level_df,
        tolerance_seconds=tolerance_seconds,
    )


def get_zero_water_levels(data: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Applique un niveau d'eau de 0 aux données de profondeur.

    :param data: Données brutes de profondeur.
    :type data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :return: Données de profondeur brutes avec un niveau d'eau de 0.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    """
    LOGGER.debug(
        f"Utilisation d'un niveau d'eau de 0 mètre pour les {len(data)} sondes."
    )

    data.loc[:, schema_ids.WATER_LEVEL_METER] = 0.0

    return data


def apply_georeference_bathymetry(
    data: gpd.GeoDataFrame,
    waterline: WaterlineProtocol,
    sounder: SensorProtocol,
    decimal_precision: int,
) -> gpd.GeoDataFrame:
    """
    Applique la transformation de géoréférencement des données de bathymétrie.

    :param data: Données brutes de profondeur.
    :type data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :param waterline: Données de la ligne d'eau.
    :type waterline: WaterlineProtocol
    :param sounder: Données du sondeur.
    :type sounder: SensorProtocol
    :param decimal_precision: Précision décimale pour les valeurs de profondeur.
    :type decimal_precision: int
    :return: Données de profondeur géoréférencées.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    """
    LOGGER.debug(f"Application des niveaux d'eau et des bras de levier aux sondes.")

    data.loc[:, schema_ids.DEPTH_PROCESSED_METER] = round(
        (
            data[schema_ids.DEPTH_RAW_METER]
            - data[schema_ids.WATER_LEVEL_METER]
            - waterline.z
            + sounder.z
        ),
        decimal_precision,
    )

    return data


def compute_order(
    data: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """
    Calcule l'ordre de la TVU et de la THU des données de bathymétrie.

    :param data: Données brut de profondeur.
    :type data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :return: Données de profondeur avec l'ordre de la TVU et de la THU.
    :rtype: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    """
    LOGGER.debug(
        f"Calcul de l'ordre IHO selon la TVU et la THU des données de profondeur."
    )

    depths = data[schema_ids.DEPTH_RAW_METER].values
    tvus = data[schema_ids.UNCERTAINTY].values
    thus = data[schema_ids.THU].values

    # Calcul vectorisé des ordres avec les fonctions optimisées
    tvu_orders = order.calculate_vertical_order_vectorized(depths, tvus)
    thu_orders = order.calculate_horizontal_order_vectorized(depths, thus)

    # Maximum des deux ordres
    final_orders = np.maximum(tvu_orders, thu_orders)
    data.loc[:, schema_ids.IHO_ORDER] = pd.Series(final_orders, index=data.index).map(
        order.ORDER_NAME_MAP
    )

    return data


@schema.validate_schemas(
    data=schema.DataLoggerWithTideZoneSchema,
    return_schema=schema.DataLoggerWithTideZoneSchema,
)
def georeference_bathymetry(
    data: gpd.GeoDataFrame,
    waterline: WaterlineProtocol,
    sounder: SensorProtocol,
    water_level: Optional[dict[str, pd.DataFrame]] = None,
    water_level_tolerance: Optional[pd.Timedelta] = pd.Timedelta("15 min"),
    decimal_precision: Optional[int] = 2,
    overwrite: Optional[bool] = False,
    apply_water_level: Optional[bool] = True,
) -> gpd.GeoDataFrame:
    """
    Géoréférence les données de bathymétrie.

    :param data: Données brutes de profondeur.
    :type data: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :param waterline: Données de la ligne d'eau.
    :type waterline: WaterlineProtocol
    :param sounder: Données du sondeur.
    :type sounder: SensorProtocol
    :param water_level: Niveau d'eau.
    :type water_level: Optional[dict[str, pd.DataFrame[schema.WaterLevelSerieDataWithMetaDataSchema]]]
    :param water_level_tolerance: Tolérance de temps pour la récupération de la valeur du niveau d'eau.
    :type water_level_tolerance: Optional[pd.Timedelta]
    :param decimal_precision: Précision décimale pour les valeurs de profondeur.
    :type decimal_precision: Optional[int]
    :param overwrite: Géoréférencer les données de profondeur même si elles ont déjà été géoréférencées.
    :type overwrite: Optional[bool]
    :param apply_water_level: True pour appliquer le niveau d'eau, sinon un niveau d'eau de 0 sera appliqué.
    :type apply_water_level: Optional[bool]
    :rtype: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema]
    :raises WaterLevelDataRequiredError: Erreur si les données de niveau d'eau sont requises.
    """
    if apply_water_level and water_level is None:
        raise WaterLevelDataRequiredError()

    data_to_process: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema] = (
        data if overwrite else data[data[schema_ids.DEPTH_PROCESSED_METER].isna()]
    )

    LOGGER.info(
        f"Géoréférencement des données bathymétriques : {len(data_to_process):,} sondes à traiter."
    )

    LOGGER.info("Récupération des niveaux d'eau pour les sondes.")
    data_to_process: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema] = (
        (
            get_water_levels_vectorized(
                data=data_to_process,
                water_level_data=water_level,
                water_level_tolerance=water_level_tolerance,
            )
        )
        if apply_water_level
        else get_zero_water_levels(data=data_to_process)
    )

    LOGGER.info("Application des niveaux d'eau et des bras de levier aux sondes.")
    data_to_process: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema] = (
        apply_georeference_bathymetry(
            data=data_to_process,
            waterline=waterline,
            sounder=sounder,
            decimal_precision=decimal_precision,
        )
    )

    LOGGER.info("Calcul de l'incertitude verticale des données de profondeur.")
    data_to_process: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema] = (
        uncertainty.compute_tvu(
            data=data_to_process,
            decimal_precision=decimal_precision,
            constant_tvu=0 if not apply_water_level else None,
        )
    )

    LOGGER.info("Calcul de l'incertitude horizontale des données de profondeur.")
    data_to_process: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema] = (
        uncertainty.compute_thu(
            data=data_to_process, decimal_precision=decimal_precision
        )
    )

    LOGGER.info("Calcul de l'ordre IHO selon la TVU et la THU.")
    data_to_process: gpd.GeoDataFrame[schema.DataLoggerWithTideZoneSchema] = (
        compute_order(data=data_to_process)
    )

    data.update(data_to_process)  # Mise à jour des données

    LOGGER.info(f"Géoréférencement des données bathymétrique terminé.")
    LOGGER.success(
        f"{data_to_process['Depth_processed_meter'].notna().sum():,} sondes géoréférencées."
    )

    depth_nan: np.int64 = data[schema_ids.DEPTH_PROCESSED_METER].isna().sum()
    if depth_nan > 0:
        LOGGER.warning(
            f"Il reste {depth_nan:,} sondes sans valeur de profondeur réduite."
        )

    return data
