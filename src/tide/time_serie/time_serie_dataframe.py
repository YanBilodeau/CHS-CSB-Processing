"""
Module pour la gestion des données de séries temporelles de marée.

Ce module contient les fonctions pour gérer les données de séries temporelles de marée.
"""

from datetime import timedelta, datetime
from typing import Optional, Any, Collection

from loguru import logger
import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline

from .exception_time_serie import get_data_gaps_message, InterpolationValueError
from .time_serie_models import (
    TimeSeriesProtocol,
    StationsHandlerProtocol,
)
from .time_serie_retry import interpolation_retry
import schema
from schema import model_ids as schema_ids

LOGGER = logger.bind(name="CSB-Pipeline.TimeSerie")
NanDateRow = dict[str, Any]
"""Dictionnaire pour une ligne de données avec une valeur de NaN."""


def get_row_by_index(wl_dataframe: pd.DataFrame, index: int) -> pd.DataFrame:
    """
    Récupère une ligne du DataFrame par son index.

    :param wl_dataframe: DataFrame contenant les données.
    :type wl_dataframe: pd.DataFrame
    :param index: Index de la ligne à récupérer.
    :type index: int
    :return: Ligne du DataFrame.
    :rtype: pd.DataFrame
    """
    row: pd.DataFrame = pd.DataFrame(
        [wl_dataframe.iloc[index]], columns=wl_dataframe.columns
    ).astype(wl_dataframe.dtypes.to_dict())

    return row


def get_first_and_last_rows(
    wl_dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Récupère la première et la dernière ligne du DataFrame.

    :param wl_dataframe: DataFrame contenant les données.
    :type wl_dataframe: pd.DataFrame
    :return: Première et dernière ligne du DataFrame.
    :rtype: tuple[pd.DataFrame, pd.DataFrame]
    """
    return get_row_by_index(wl_dataframe=wl_dataframe, index=0), get_row_by_index(
        wl_dataframe=wl_dataframe, index=-1
    )


def extend_rows_to_deltatime(
    non_nan_dataframe: pd.DataFrame, first_row: pd.DataFrame, last_row: pd.DataFrame
) -> pd.DataFrame:
    """
    Étend les lignes du DataFrame pour ajouter la première et la dernière date.

    :param non_nan_dataframe: DataFrame contenant les données non NaN.
    :type non_nan_dataframe: pd.DataFrame
    :param first_row: Première ligne du DataFrame.
    :type first_row: pd.DataFrame
    :param last_row: Dernière ligne du DataFrame.
    :type last_row: pd.DataFrame
    :return: DataFrame contenant les données étendues.
    :rtype: pd.DataFrame
    """
    if first_row[schema_ids.VALUE].isna().all():
        non_nan_dataframe = pd.concat([first_row, non_nan_dataframe])

    if last_row[schema_ids.VALUE].isna().all():
        non_nan_dataframe = pd.concat([non_nan_dataframe, last_row])

    return non_nan_dataframe


def extend_non_nan_dataframe(
    non_nan_dataframe: pd.DataFrame, first_row: pd.DataFrame, last_row: pd.DataFrame
) -> pd.DataFrame:
    """
    Étend les lignes du DataFrame pour ajouter la première et la dernière date.

    :param non_nan_dataframe: DataFrame contenant les données non NaN.
    :type non_nan_dataframe: pd.DataFrame
    :param first_row: Première ligne du DataFrame.
    :type first_row: pd.DataFrame
    :param last_row: Dernière ligne du DataFrame.
    :type last_row: pd.DataFrame
    :return: DataFrame contenant les données étendues.
    :rtype: pd.DataFrame
    """
    non_nan_dataframe = extend_rows_to_deltatime(
        non_nan_dataframe=non_nan_dataframe, first_row=first_row, last_row=last_row
    )
    reset_and_sort_index(wl_dataframe=non_nan_dataframe, drop=True)
    non_nan_dataframe["data_time_gap"] = non_nan_dataframe[schema_ids.EVENT_DATE].diff()

    return non_nan_dataframe


def identify_interpolation_and_fill_gaps(
    gaps_dataframe: pd.DataFrame, threshold_interpolation_filling: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Identifie les périodes de données manquantes à interpoler et à remplir.

    :param gaps_dataframe: DataFrame contenant les périodes de données manquantes.
    :type gaps_dataframe: pd.DataFrame[schema.TimeSerieDataSchema]
    :param threshold_interpolation_filling: Seuil de temps en dessous duquel les données manquantes sont interpolées ou remplies.
    :type threshold_interpolation_filling: str
    :return: Périodes de données manquantes à interpoler et à remplir.
    :rtype: tuple[pd.DataFrame[schema.TimeSerieDataSchema], pd.DataFrame[schema.TimeSerieDataSchema]]
    """
    gaps_to_interpolate: pd.DataFrame[schema.TimeSerieDataSchema] = gaps_dataframe[
        gaps_dataframe["data_time_gap"] < pd.Timedelta(threshold_interpolation_filling)
    ]
    gaps_to_fill: pd.DataFrame[schema.TimeSerieDataSchema] = gaps_dataframe[
        gaps_dataframe["data_time_gap"] >= pd.Timedelta(threshold_interpolation_filling)
    ]

    return gaps_to_interpolate, gaps_to_fill


def identify_data_gaps(
    wl_dataframe: pd.DataFrame,
    max_time_gap: str,
    threshold_interpolation_filling: Optional[str | None] = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Identifie les périodes de données manquantes.

    :param wl_dataframe: DataFrame contenant les données.
    :type wl_dataframe: pd.DataFrame[schema.TimeSerieDataSchema]
    :param max_time_gap: Intervalle de temps maximale permise avant de  combler les données manquantes.
    :type max_time_gap: str
    :param threshold_interpolation_filling: Seuil de temps en dessous duquel les données manquantes sont interpolées ou remplies.
                                            Si None, les données manquantes sont seulement remplies par la time série suivante.
    :type threshold_interpolation_filling: Optional[str | None]
    :return: Un tuple contenant toutes les périodes de données manquantes, les périodes de données manquantes à interpoler
             et les périodes de données manquantes à remplir.
    :rtype: tuple[pd.DataFrame[schema.TimeSerieDataSchema], pd.DataFrame[schema.TimeSerieDataSchema], pd.DataFrame[schema.TimeSerieDataSchema]]
    """
    LOGGER.debug(
        f"Identification des périodes de données manquantes de plus de {max_time_gap} pour "
        f"{wl_dataframe[schema_ids.TIME_SERIE_CODE].unique()}."
    )

    first_row, last_row = get_first_and_last_rows(wl_dataframe=wl_dataframe)

    non_nan_dataframe: pd.DataFrame = wl_dataframe.dropna(subset=[schema_ids.VALUE])
    non_nan_dataframe: pd.DataFrame = extend_non_nan_dataframe(
        non_nan_dataframe=non_nan_dataframe, first_row=first_row, last_row=last_row
    )

    gaps_dataframe: pd.DataFrame[schema.TimeSerieDataSchema] = non_nan_dataframe[
        non_nan_dataframe["data_time_gap"] > pd.Timedelta(max_time_gap)
    ]

    if threshold_interpolation_filling is None:
        return gaps_dataframe, pd.DataFrame(), gaps_dataframe

    gaps_to_interpolate, gaps_to_fill = identify_interpolation_and_fill_gaps(
        gaps_dataframe=gaps_dataframe,
        threshold_interpolation_filling=threshold_interpolation_filling,
    )

    return gaps_dataframe, gaps_to_interpolate, gaps_to_fill


def resample_data(wl_dataframe: pd.DataFrame, time: str) -> pd.DataFrame:
    """
    Rééchantillonne les données.

    :param wl_dataframe: DataFrame contenant les données.
    :type wl_dataframe: pd.DataFrame[schema.TimeSerieDataSchema]
    :param time: Intervalle de temps.
    :type time: str
    :return: DataFrame contenant les données rééchantillonnées.
    :rtype: pd.DataFrame
    """
    LOGGER.debug(
        f"Rééchantillonnage des données avec un intervalle de temps de {time}."
    )

    wl_resampled: pd.DataFrame = wl_dataframe.resample(time).asfreq()
    wl_resampled[schema_ids.TIME_SERIE_CODE] = wl_resampled[
        schema_ids.TIME_SERIE_CODE
    ].fillna(f"{wl_dataframe[schema_ids.TIME_SERIE_CODE].unique()[0]}-interpolated")

    return wl_resampled


def cubic_spline_interpolation(
    index_time: pd.Index, values: pd.Series, wl_resampled: pd.DataFrame
) -> pd.DataFrame:
    """
    Interpole les données manquantes avec une spline cubique.

    :param index_time: Index des données.
    :type index_time: pd.Index
    :param values: Valeurs des données.
    :type values: pd.Series
    :param wl_resampled: DataFrame contenant les données rééchantillonnées.
    :type wl_resampled: pd.DataFrame
    :return: DataFrame contenant les données interpolées.
    :rtype: pd.DataFrame
    """
    if values.isna().any():
        LOGGER.warning(
            "L'interpolation cubique slpine ne peut pas être effectuée avec des données manquantes. "
            "Des données manquantes ont été détectées dans les données de niveau d'eau de "
            f"{wl_resampled.index[0]} à {wl_resampled.index[-1]}."
        )

        raise InterpolationValueError(
            from_time=wl_resampled.index[0], to_time=wl_resampled.index[-1]
        )

    LOGGER.debug("Interpolation des données manquantes avec une spline cubique.")

    cubic_spline_interplation: CubicSpline = CubicSpline(index_time, values)
    # Convertir l'index en valeur numérique
    wl_resampled[schema_ids.VALUE] = cubic_spline_interplation(
        wl_resampled.index.astype(np.int64) // 10**9
    )

    return wl_resampled


def reset_and_sort_index(
    wl_dataframe: pd.DataFrame,
    drop: bool,
    inplace: bool = True,
) -> None:
    """
    Réinitialise et trie l'index du DataFrame.

    :param drop: Si True, supprime l'ancien index.
    :type drop: bool
    :param inplace: Si True, modifie le DataFrame en place.
    :type inplace: bool
    :param wl_dataframe: DataFrame contenant les données.
    :type wl_dataframe: pd.DataFrame
    """
    LOGGER.debug("Réinitialisation de l'index et trie par event_date du DataFrame.")

    wl_dataframe.sort_values(by=schema_ids.EVENT_DATE, inplace=inplace)  # type: ignore
    wl_dataframe.reset_index(inplace=inplace, drop=drop)


def interpolate_data_gaps(
    wl_dataframe: pd.DataFrame, gaps_dataframe: pd.DataFrame, max_time_gap: str
) -> pd.DataFrame:
    """
    Interpole les données manquantes.

    :param wl_dataframe: DataFrame contenant les données.
    :type wl_dataframe: pd.DataFrame[schema.TimeSerieDataSchema]
    :param gaps_dataframe: DataFrame contenant les périodes de données manquantes à interpoler.
    :type gaps_dataframe: pd.DataFrame
    :param max_time_gap: Intervalle de temps maximale permise avant de combler les données manquantes.
    :type max_time_gap: str
    :return: DataFrame contenant les données interpolées.
    :rtype: pd.DataFrame[schema.TimeSerieDataSchema]
    """
    LOGGER.debug(
        f"Interpolation des données manquantes de {wl_dataframe[schema_ids.TIME_SERIE_CODE].unique()}."
    )

    wl_dataframe.set_index(schema_ids.EVENT_DATE, inplace=True)

    wl_resampled: pd.DataFrame = resample_data(
        wl_dataframe=wl_dataframe, time=max_time_gap
    )

    # Convertir l'index en valeur numérique pour l'interpolation
    time: pd.Index = wl_dataframe.index.astype(np.int64) // 10**9
    water_level_values: pd.Series = wl_dataframe[schema_ids.VALUE]

    wl_resampled = cubic_spline_interpolation(
        index_time=time, values=water_level_values, wl_resampled=wl_resampled
    )

    reset_and_sort_index(wl_dataframe=wl_dataframe, drop=False)
    reset_and_sort_index(wl_dataframe=wl_resampled, drop=False)

    return process_gaps_to_fill(
        gaps_dataframe=gaps_dataframe,
        wl_dataframe=wl_resampled,
        wl_combined_dataframe=wl_dataframe,
    )


def process_gaps_to_interpolate(
    wl_dataframe: pd.DataFrame,
    max_time_gap: str,
    threshold_interpolation_filling: Optional[str | None] = None,
) -> pd.DataFrame:
    """
    Identifie et comble les données manquantes avec une interpolation.

    :param wl_dataframe: DataFrame contenant les données.
    :type wl_dataframe: pd.DataFrame[schema.TimeSerieDataSchema]
    :param max_time_gap: Intervalle de temps maximale permise avant de  combler les données manquantes.
    :type max_time_gap: str
    :param threshold_interpolation_filling: Seuil de temps en dessous duquel les données manquantes sont interpolées ou remplies.
                                            Si None, les données manquantes sont seulement remplies par la time série suivante.
    :type threshold_interpolation_filling: Optional[str | None]
    :return: Données de niveau d'eau combinées.
    :Rtype: pd.DataFrame[schema.TimeSerieDataSchema]
    """
    _, gaps_to_interpolate, _ = identify_data_gaps(
        wl_dataframe=wl_dataframe,
        max_time_gap=max_time_gap,
        threshold_interpolation_filling=threshold_interpolation_filling,
    )

    if gaps_to_interpolate.empty:
        LOGGER.debug(
            f"Aucune période de données manquantes de plus de {max_time_gap} à interpoler pour "
            f"{wl_dataframe[schema_ids.TIME_SERIE_CODE].unique()}."
        )
        return wl_dataframe

    LOGGER.debug(get_data_gaps_message(gaps=gaps_to_interpolate))

    wl_dataframe: pd.DataFrame[schema.TimeSerieDataSchema] = interpolate_data_gaps(
        gaps_dataframe=gaps_to_interpolate,
        wl_dataframe=wl_dataframe,
        max_time_gap=max_time_gap,
    )

    return wl_dataframe


def get_gaps_dataframe_list(
    gaps_dataframe: pd.DataFrame, wl_dataframe: pd.DataFrame
) -> list[pd.DataFrame]:
    """
    Récupère les périodes de données manquantes.

    :param gaps_dataframe: DataFrame contenant les périodes de données manquantes.
    :type gaps_dataframe: pd.DataFrame
    :param wl_dataframe: DataFrame contenant les données.
    :type wl_dataframe: pd.DataFrame
    :return: Une liste de DataFrame contenant les périodes de données manquantes.
    :rtype: list[pd.DataFrame]
    """
    return [
        wl_dataframe[
            (
                wl_dataframe[schema_ids.EVENT_DATE]
                > row[schema_ids.EVENT_DATE] - row["data_time_gap"]
            )
            & (wl_dataframe[schema_ids.EVENT_DATE] < row[schema_ids.EVENT_DATE])
        ]
        for _, row in gaps_dataframe.iterrows()
    ]


def merge_dataframes(
    wl_combined_dataframe: pd.DataFrame, wl_dataframe: pd.DataFrame
) -> pd.DataFrame:
    """
    Fusionne les DataFrames.

    :param wl_combined_dataframe: DataFrame contenant les données combinées.
    :type wl_combined_dataframe: pd.DataFrame[schema.TimeSerieDataSchema]
    :param wl_dataframe: DataFrame contenant les données à ajouter
    :type wl_dataframe: pd.DataFrame[schema.TimeSerieDataSchema]
    :return: DataFrame contenant les données à ajouter et celles combinées.
    :rtype: pd.DataFrame[schema.TimeSerieDataSchema]
    """
    wl_combined_dataframe = wl_combined_dataframe.merge(
        wl_dataframe, on=schema_ids.EVENT_DATE, how="left", suffixes=("", "_wl")
    )

    wl_combined_dataframe[schema_ids.VALUE] = wl_combined_dataframe[
        schema_ids.VALUE
    ].combine_first(wl_combined_dataframe["value_wl"])

    wl_combined_dataframe[schema_ids.TIME_SERIE_CODE] = wl_combined_dataframe[
        schema_ids.TIME_SERIE_CODE
    ].combine_first(wl_combined_dataframe["time_serie_code_wl"])

    return wl_combined_dataframe.drop(columns=["value_wl", "time_serie_code_wl"])


def fill_data_gaps(
    gaps_dataframe: pd.DataFrame,
    wl_dataframe: pd.DataFrame,
    wl_combined_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Permet de remplir les périodes de données manquantes.

    :param gaps_dataframe: DataFrame contenant les périodes de données manquantes.
    :type gaps_dataframe: pd.DataFrame[schema.TimeSerieDataSchema]
    :param wl_dataframe: DataFrame contenant les données à ajouter.
    :type wl_dataframe: pd.DataFrame[schema.TimeSerieDataSchema]
    :param wl_combined_dataframe: DataFrame contenant les données combinées.
    :type wl_combined_dataframe: pd.DataFrame[schema.TimeSerieDataSchema]
    :return: DataFrame contenant les données ajoutées au données combinées.
    :rtype: pd.DataFrame[schema.TimeSerieDataSchema]
    """
    LOGGER.debug(
        f"Remplissage des données manquantes à partir de la série temporelle {wl_dataframe[schema_ids.TIME_SERIE_CODE].unique()}."
    )

    gaps_dataframe_list: list[pd.DataFrame[schema.TimeSerieDataSchema]] = (
        get_gaps_dataframe_list(
            gaps_dataframe=gaps_dataframe, wl_dataframe=wl_dataframe
        )
    )

    wl_combined_dataframe: pd.DataFrame[schema.TimeSerieDataSchema] = pd.concat(
        [wl_combined_dataframe] + gaps_dataframe_list
    )
    wl_combined_dataframe: pd.DataFrame[schema.TimeSerieDataSchema] = merge_dataframes(
        wl_combined_dataframe=wl_combined_dataframe, wl_dataframe=wl_dataframe
    )

    return wl_combined_dataframe


def process_gaps_to_fill(
    wl_combined_dataframe: pd.DataFrame,
    gaps_dataframe: pd.DataFrame,
    wl_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Identifie et comble les données manquantes.

    :param wl_combined_dataframe: DataFrame contenant les données combinées.
    :type wl_combined_dataframe: pd.DataFrame[schema.TimeSerieDataSchema]
    :param gaps_dataframe: DataFrame contenant les périodes de données manquantes.
    :type gaps_dataframe: pd.DataFrame[schema.TimeSerieDataSchema]
    :param wl_dataframe: DataFrame contenant les données à ajouter aux données combinées.
    :type wl_dataframe: pd.DataFrame[schema.TimeSerieDataSchema]
    :return: Données de niveau d'eau combinées.
    :rtype: pd.DataFrame[schema.TimeSerieDataSchema]
    """
    LOGGER.debug(get_data_gaps_message(gaps=gaps_dataframe))

    wl_combined_dataframe: pd.DataFrame[schema.TimeSerieDataSchema] = fill_data_gaps(
        gaps_dataframe=gaps_dataframe,
        wl_dataframe=wl_dataframe,
        wl_combined_dataframe=wl_combined_dataframe,
    )
    reset_and_sort_index(wl_dataframe=wl_combined_dataframe, drop=True)

    return wl_combined_dataframe


def combine_water_level_data(
    wl_combined_dataframe: pd.DataFrame,
    wl_data_dataframe: pd.DataFrame,
    gaps_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Combine les données de niveau d'eau.

    :param wl_combined_dataframe: DataFrame contenant les données de niveau d'eau combinées.
    :type wl_combined_dataframe: pd.DataFrame[schema.TimeSerieDataSchema]
    :param wl_data_dataframe: DataFrame contenant les données de niveau d'eau.
    :type wl_data_dataframe: pd.DataFrame[schema.TimeSerieDataSchema]
    :param gaps_dataframe: DataFrame contenant les périodes de données manquantes.
    :type gaps_dataframe: pd.DataFrame[schema.TimeSerieDataSchema]
    :return: DataFrame contenant les données de niveau d'eau combinées.
    :rtype: pd.DataFrame[schema.TimeSerieDataSchema]
    """
    if wl_combined_dataframe.empty:
        return wl_data_dataframe

    return process_gaps_to_fill(
        wl_combined_dataframe=wl_combined_dataframe,
        wl_dataframe=wl_data_dataframe,
        gaps_dataframe=gaps_dataframe,
    )


def create_nan_date_row(date_time: str) -> NanDateRow:
    """
    Crée une ligne de données avec une valeur de NaN pour une date donnée.

    :param date_time: Date.
    :type date_time: str
    :return: Ligne de données.
    :rtype: NanDateRow
    """
    return {schema_ids.EVENT_DATE: pd.to_datetime(date_time), schema_ids.VALUE: np.nan}


def add_nan_date_row(wl_dataframe: pd.DataFrame, time: str) -> pd.DataFrame:
    """
    Ajoute une ligne de données avec une valeur de NaN à partir d'une date.

    :param wl_dataframe: DataFrame contenant les données.
    :type wl_dataframe: pd.DataFrame[schema.TimeSerieDataSchema]
    :param time: Date.
    :type time: str
    :return: DataFrame contenant la ligne ajouter aux autres données.
    :rtype: pd.DataFrame[schema.TimeSerieDataSchema]
    """
    LOGGER.debug(f"Ajout d'une ligne de données NaN à partir de la date '{time}'.")

    wl_dataframe.loc[len(wl_dataframe)] = create_nan_date_row(date_time=time)
    reset_and_sort_index(wl_dataframe=wl_dataframe, drop=True)

    return wl_dataframe


def clean_time_series_data(
    wl_dataframe: pd.DataFrame,
    from_time: str,
    to_time: str,
) -> pd.DataFrame:
    """
    Nettoie les données de la série temporelle.

    :param wl_dataframe: Données de la série temporelle.
    :type wl_dataframe: pd.DataFrame[schema.TimeSerieDataSchema]
    :param from_time: Date de début.
    :type from_time: str
    :param to_time: Date de fin.
    :type to_time: str
    :return: Données de la série temporelle nettoyées.
    :rtype: pd.DataFrame[schema.TimeSerieDataSchema]
    """
    LOGGER.debug(
        "Nettoyage des données de la série temporelle et validation du temps de début et de fin."
    )

    wl_dataframe.dropna(subset=[schema_ids.VALUE], inplace=True)

    if wl_dataframe[schema_ids.EVENT_DATE].iloc[0] > pd.to_datetime(from_time):
        wl_dataframe = add_nan_date_row(wl_dataframe=wl_dataframe, time=from_time)

    if wl_dataframe[schema_ids.EVENT_DATE].iloc[-1] < pd.to_datetime(to_time):
        wl_dataframe = add_nan_date_row(wl_dataframe=wl_dataframe, time=to_time)

    return wl_dataframe


def get_time_series_data(
    stations_handler: StationsHandlerProtocol,
    station_id: str,
    from_time: str,
    to_time: str,
    time_serie_code: TimeSeriesProtocol,
    buffer_time: Optional[timedelta] = None,
    wlo_qc_flag_filter: Optional[list[str] | None] = None,
) -> pd.DataFrame | None:
    """
    Récupère les données de la série temporelle.

    :param stations_handler: Gestionnaire des stations.
    :type stations_handler: StationsHandlerProtocol
    :param station_id: Identifiant de la station.
    :type station_id: str
    :param from_time: Date de début.
    :type from_time: str
    :param to_time: Date de fin.
    :type to_time: str
    :param time_serie_code: Série temporelle.
    :type time_serie_code: TimeSeriesProtocol
    :param buffer_time: Temps tampon à ajouter au début et à la fin de la période de données.
    :type buffer_time: Optional[timedelta]
    :param wlo_qc_flag_filter: Filtre de qualité des données wlo.
    :type wlo_qc_flag_filter: Optional[list[str] | None]
    :return: Données de la série temporelle.
    :rtype: pd.DataFrame[schema.TimeSerieDataSchema] | None
    """
    if buffer_time:
        LOGGER.debug(
            f"Récupération des données de la série temporelle {time_serie_code} pour la station {station_id} "
            f"de {from_time} à {to_time} avec un temps tampon de {buffer_time}."
        )
    from_time_buffered: str = (
        get_iso8601_from_datetime(get_datetime_from_iso8601(from_time) - buffer_time)
        if buffer_time
        else from_time
    )
    to_time_buffered: str = (
        get_iso8601_from_datetime(get_datetime_from_iso8601(to_time) + buffer_time)
        if buffer_time
        else to_time
    )

    wl_data: pd.DataFrame[schema.TimeSerieDataSchema] = (
        stations_handler.get_time_series_dataframe(
            station=station_id,
            from_time=from_time_buffered,
            to_time=to_time_buffered,
            time_serie_code=time_serie_code,
            wlo_qc_flag_filter=wlo_qc_flag_filter,
        )
    )

    if wl_data.empty:
        return None

    return clean_time_series_data(
        wl_dataframe=wl_data, from_time=from_time, to_time=to_time
    )


def get_empty_dataframe() -> pd.DataFrame:
    """
    Crée un DataFrame vide.

    :return: DataFrame vide.
    :rtype: pd.DataFrame
    """
    return pd.DataFrame(columns=list(schema.TimeSerieDataSchema.__annotations__.keys()))


def get_datetime_from_iso8601(date: str) -> datetime:
    """
    Convertit une date ISO 8601 en objet datetime.

    :param date: Date ISO 8601.
    :type date: str
    :return: Objet datetime.
    :rtype: datetime
    """
    return datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")


def get_iso8601_from_datetime(date: datetime) -> str:
    """
    Convertit un objet datetime en date ISO 8601.

    :param date: Objet datetime.
    :type date: datetime
    :return: Date ISO 8601.
    :rtype: str
    """
    return date.strftime("%Y-%m-%dT%H:%M:%SZ")


@interpolation_retry()
def get_water_level_data(
    stations_handler: StationsHandlerProtocol,
    station_id: str,
    from_time: str,
    to_time: str,
    time_series_priority: Collection[TimeSeriesProtocol],
    buffer_time: Optional[timedelta | None] = None,
    max_time_gap: Optional[str | None] = None,
    threshold_interpolation_filling: Optional[str | None] = None,
    wlo_qc_flag_filter: Optional[list[str] | None] = None,
) -> pd.DataFrame:
    """
    Récupère et traite les séries temporelles de niveau d'eau pour une station donnée.

    :param stations_handler: Gestionnaire des stations.
    :type stations_handler: StationsHandlerProtocol
    :param station_id: Identifiant de la station.
    :type station_id: str
    :param from_time: Date de début.
    :type from_time: str
    :param to_time: Date de fin.
    :type to_time: str
    :param time_series_priority: Liste des séries temporelles à récupérer en ordre de priorité.
    :type time_series_priority: Collection[TimeSeriesProtocol]
    :param buffer_time: Temps tampon à ajouter au début et à la fin de la période de données.
    :type buffer_time: Optional[timedelta | None]
    :param max_time_gap: Intervalle de temps maximal permis. Si None, l'interpolation et le remplissage des données manquantes est désactivée.
    :type max_time_gap: Optional[str | None]
    :param threshold_interpolation_filling: Seuil de temps en dessous duquel les données manquantes sont interpolées ou remplies.
                                            Si None, les données manquantes sont seulement remplies par la time série suivante.
    :type threshold_interpolation_filling: Optional[str | None]
    :param wlo_qc_flag_filter: Filtre de qualité des données wlo.
    :type wlo_qc_flag_filter: Optional[list[str] | None]
    :return: Données de niveau d'eau combinées.
    :rtype: pd.DataFrame[schema.TimeSerieDataSchema]
    """
    wl_combined: pd.DataFrame = get_empty_dataframe()

    for index, time_serie in enumerate(time_series_priority):
        wl_data: pd.DataFrame[schema.TimeSerieDataSchema] = get_time_series_data(
            stations_handler=stations_handler,
            station_id=station_id,
            from_time=from_time,
            to_time=to_time,
            time_serie_code=time_serie,
            buffer_time=buffer_time,
            wlo_qc_flag_filter=wlo_qc_flag_filter,
        )

        if wl_data is None:
            LOGGER.debug(
                f"Aucune donnée {time_serie} n'a été récupérée pour la station {station_id} de {from_time} à {to_time}."
            )
            continue

        if max_time_gap is None:
            LOGGER.debug(
                f"L'interpolation et le remplissage des données manquantes est désactivée pour la station {station_id}."
            )
            return wl_data

        gaps_total, _, gaps_to_fill = identify_data_gaps(
            wl_dataframe=wl_data if wl_combined.empty else wl_combined,
            max_time_gap=max_time_gap,
            threshold_interpolation_filling=threshold_interpolation_filling,
        )

        if gaps_total.empty:
            LOGGER.debug(
                f"Aucune donnée manquante pour la station {station_id} avec les séries temporelles: "
                f"{time_series_priority[:index + 1]}."
            )
            wl_combined = wl_data if wl_combined.empty else wl_combined
            break

        wl_data: pd.DataFrame[schema.TimeSerieDataSchema] = process_gaps_to_interpolate(
            wl_dataframe=wl_data,
            max_time_gap=max_time_gap,
            threshold_interpolation_filling=threshold_interpolation_filling,
        )

        # todo : identifier les données manquantes après interpolation ?

        wl_combined: pd.DataFrame[schema.TimeSerieDataSchema] = (
            combine_water_level_data(
                wl_combined_dataframe=wl_combined,
                wl_data_dataframe=wl_data,
                gaps_dataframe=gaps_to_fill,
            )
        )

    else:
        LOGGER.debug(
            f"Toutes les séries temporelles disponibles pour la station {station_id} ont été traitées: {time_series_priority}."
        )

    return wl_combined


# todo isTidal == False  -> interpolation linéaire plutôt que spline cubique ?
# todo problème avec l'interpolation si les données sont manquantes à la fin ou au début de la période NaN
# todo Valider qu' il y a au moins x heure de part et d autre pour faire l interpolation, sinon raise exception
# todo valider le holding avant de demander les données (n'enlève pas les trous de moins de 10 jours) seulement pour wlo ! -> sinon refaire les polygon sans cette station ?
