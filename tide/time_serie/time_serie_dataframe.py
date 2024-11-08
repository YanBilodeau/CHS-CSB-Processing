from datetime import timedelta, datetime
from functools import partial
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, before_log
from typing import Optional, Any, Collection

import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline

from loguru import logger

from .time_serie_models import (
    DataGapPeriod,
    TimeSeriesProtocol,
    StationsHandlerProtocol,
)
from ..schema import TimeSerieDataSchema

LOGGER = logger.bind(name="CSB-Pipeline.TimeSerie")

NanDateRow = dict[str, Any]


def double_buffer_time(retry_state) -> None:
    buffer_time = retry_state.kwargs.get("buffer_time")

    if buffer_time is None:
        buffer_time = timedelta(hours=24)

    LOGGER.debug(
        f"Augmentation du temps tampon pour la prochaine tentative d'interpolation de "
        f"{retry_state.kwargs.get('buffer_time')} à {buffer_time * 2}."
    )

    retry_state.kwargs["buffer_time"] = buffer_time * 2


LEVEL: str = "TRACE"
retry_tenacity = partial(
    retry,
    stop=stop_after_attempt(5),
    wait=wait_exponential_jitter(initial=1, jitter=1, max=3),
    before=before_log(LOGGER, LEVEL),  # type: ignore
    after=double_buffer_time,
)


def get_row_by_index(wl_dataframe: pd.DataFrame, index: int) -> pd.DataFrame:
    """
    Récupère une ligne du DataFrame par son index.

    :param wl_dataframe: (pd.DataFrame) DataFrame contenant les données.
    :param index: (int) Index de la ligne à récupérer.
    :return: (pd.DataFrame) Ligne du DataFrame.
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

    :param wl_dataframe: (pd.DataFrame) DataFrame contenant les données.
    :return: (tuple[pd.DataFrame, pd.DataFrame]) Première et dernière ligne du DataFrame.
    """
    return get_row_by_index(wl_dataframe=wl_dataframe, index=0), get_row_by_index(
        wl_dataframe=wl_dataframe, index=-1
    )


def extend_rows_to_deltatime(
    non_nan_dataframe: pd.DataFrame, first_row: pd.DataFrame, last_row: pd.DataFrame
) -> pd.DataFrame:
    """
    Étend les lignes du DataFrame pour ajouter la première et la dernière date.

    :param non_nan_dataframe: (pd.DataFrame) DataFrame contenant les données non NaN.
    :param first_row: (pd.DataFrame) Première ligne du DataFrame.
    :param last_row: (pd.DataFrame) Dernière ligne du DataFrame.
    :return: (pd.DataFrame) DataFrame contenant les données étendues.
    """
    if first_row["value"].isna().all():
        non_nan_dataframe = pd.concat([first_row, non_nan_dataframe])

    if last_row["value"].isna().all():
        non_nan_dataframe = pd.concat([non_nan_dataframe, last_row])

    return non_nan_dataframe


def extend_non_nan_dataframe(
    non_nan_dataframe: pd.DataFrame, first_row: pd.DataFrame, last_row: pd.DataFrame
) -> pd.DataFrame:
    """
    Étend les lignes du DataFrame pour ajouter la première et la dernière date.

    :param non_nan_dataframe: (pd.DataFrame) DataFrame contenant les données non NaN.
    :param first_row: (pd.DataFrame) Première ligne du DataFrame.
    :param last_row: (pd.DataFrame) Dernière ligne du DataFrame.
    :return: (pd.DataFrame) DataFrame contenant les données étendues.
    """
    non_nan_dataframe = extend_rows_to_deltatime(
        non_nan_dataframe=non_nan_dataframe, first_row=first_row, last_row=last_row
    )
    reset_and_sort_index(wl_dataframe=non_nan_dataframe, drop=True)
    non_nan_dataframe["data_time_gap"] = non_nan_dataframe["event_date"].diff()

    return non_nan_dataframe


def identify_interpolation_and_fill_gaps(
    gaps_dataframe: pd.DataFrame, threshold_interpolation_filling: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Identifie les périodes de données manquantes à interpoler et à remplir.

    :param gaps_dataframe: (pd.DataFrame[TimeSerieDataSchema]) DataFrame contenant les périodes de données manquantes.
    :param threshold_interpolation_filling: (str) Seuil de temps en dessous duquel les données manquantes sont interpolées
                                                ou remplies.
    :return: (tuple[pd.DataFrame[TimeSerieDataSchema], pd.DataFrame[TimeSerieDataSchema]]) Périodes de données manquantes
                    à interpoler et à remplir.
    """
    gaps_to_interpolate: pd.DataFrame[TimeSerieDataSchema] = gaps_dataframe[
        gaps_dataframe["data_time_gap"] < pd.Timedelta(threshold_interpolation_filling)
    ]
    gaps_to_fill: pd.DataFrame[TimeSerieDataSchema] = gaps_dataframe[
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

    :param wl_dataframe: (pd.DataFrame[TimeSerieDataSchema]) DataFrame contenant les données.
    :param max_time_gap: (str) Intervalle de temps maximale permise avant de  combler les données manquantes.
    :param threshold_interpolation_filling: (Optional[str | None]) Seuil de temps en dessous duquel les données
                                                manquantes sont interpolées ou remplies. Si None, les données manquantes
                                                sont seulement remplies par la time série suivante.
    :return: (tuple[pd.DataFrame[TimeSerieDataSchema], pd.DataFrame[TimeSerieDataSchema], pd.DataFrame[TimeSerieDataSchema]])
                    Un tuple contenant toutes les périodes de données manquantes, les périodes de données manquantes
                    à interpoler et les périodes de données manquantes à remplir.
    """
    LOGGER.debug(
        f"Identification des périodes de données manquantes de plus de {max_time_gap} pour "
        f"{wl_dataframe['time_serie_code'].unique()}."
    )

    first_row, last_row = get_first_and_last_rows(wl_dataframe=wl_dataframe)

    non_nan_dataframe: pd.DataFrame = wl_dataframe.dropna(subset=["value"])
    non_nan_dataframe: pd.DataFrame = extend_non_nan_dataframe(
        non_nan_dataframe=non_nan_dataframe, first_row=first_row, last_row=last_row
    )

    gaps_dataframe: pd.DataFrame[TimeSerieDataSchema] = non_nan_dataframe[
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

    :param wl_dataframe: (pd.DataFrame) DataFrame contenant les données.
    :param time: (str) Intervalle de temps.
    :return: (pd.DataFrame) DataFrame contenant les données rééchantillonnées.
    """
    LOGGER.debug(
        f"Rééchantillonnage des données avec un intervalle de temps de {time}."
    )

    wl_resampled: pd.DataFrame = wl_dataframe.resample(time).asfreq()
    wl_resampled["time_serie_code"] = wl_resampled["time_serie_code"].fillna(
        f"{wl_dataframe['time_serie_code'].unique()[0]}-interpolated"
    )

    return wl_resampled


def cubic_spline_interpolation(
    index_time: pd.Index, values: pd.Series, wl_resampled: pd.DataFrame
) -> pd.DataFrame:
    """
    Interpole les données manquantes avec une spline cubique.

    :param index_time: (pd.Index) Index des données.
    :param values: (pd.Series) Valeurs des données.
    :param wl_resampled: (pd.DataFrame) DataFrame contenant les données rééchantillonnées.
    :return: (pd.DataFrame) DataFrame contenant les données interpolées.
    """
    LOGGER.debug("Interpolation des données manquantes avec une spline cubique.")

    cubic_spline_interplation: CubicSpline = CubicSpline(index_time, values)
    wl_resampled["value"] = cubic_spline_interplation(
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

    :param drop: (bool) Si True, supprime l'ancien index.
    :param inplace: (bool) Si True, modifie le DataFrame en place.
    :param wl_dataframe: (pd.DataFrame) DataFrame contenant les données.
    """
    LOGGER.debug("Réinitialisation de l'index et trie par event_date du DataFrame.")

    wl_dataframe.sort_values(by="event_date", inplace=inplace)  # type: ignore
    wl_dataframe.reset_index(inplace=inplace, drop=drop)


def interpolate_data_gaps(
    wl_dataframe: pd.DataFrame, gaps_dataframe: pd.DataFrame, max_time_gap: str
) -> pd.DataFrame:
    """
    Interpole les données manquantes.

    :param wl_dataframe: (pd.DataFrame) DataFrame contenant les données.
    :param gaps_dataframe: (pd.DataFrame) DataFrame contenant les périodes de données manquantes à interpoler.
    :param max_time_gap: (str) Intervalle de temps maximale permise avant de combler les données manquantes.
    :return: (pd.DataFrame) DataFrame contenant les données interpolées.
    """
    LOGGER.debug(
        f"Interpolation des données manquantes de {wl_dataframe['time_serie_code'].unique()}."
    )

    wl_dataframe.set_index("event_date", inplace=True)

    wl_resampled: pd.DataFrame = resample_data(
        wl_dataframe=wl_dataframe, time=max_time_gap
    )

    # Convertir l'index en valeur numérique pour l'interpolation
    time: pd.Index = wl_dataframe.index.astype(np.int64) // 10**9
    water_level_values: pd.Series = wl_dataframe["value"]

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

    :param wl_dataframe: (pd.DataFrame) DataFrame contenant les données.
        :param max_time_gap: (str) Intervalle de temps maximale permise avant de  combler les données manquantes.
    :param threshold_interpolation_filling: (Optional[str | None]) Seuil de temps en dessous duquel les données
                                                manquantes sont interpolées ou remplies. Si None, les données manquantes
                                                sont seulement remplies par la time série suivante.
    :return: (pd.DataFrame[TimeSerieDataSchema]]) Données de niveau d'eau combinées.
    """
    _, gaps_to_interpolate, _ = identify_data_gaps(
        wl_dataframe=wl_dataframe,
        max_time_gap=max_time_gap,
        threshold_interpolation_filling=threshold_interpolation_filling,
    )

    if gaps_to_interpolate.empty:
        LOGGER.debug(
            f"Aucune période de données manquantes de plus de {max_time_gap} à interpoler pour "
            f"{wl_dataframe['time_serie_code'].unique()}."
        )
        return wl_dataframe

    LOGGER.debug(get_data_gaps_message(gaps=gaps_to_interpolate))

    wl_dataframe: pd.DataFrame[TimeSerieDataSchema] = interpolate_data_gaps(
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

    :param gaps_dataframe: (pd.DataFrame) DataFrame contenant les périodes de données manquantes.
    :param wl_dataframe: (pd.DataFrame) DataFrame contenant les données.
    :return: (list[pd.DataFrame]) Une liste de DataFrame contenant les périodes de données manquantes.
    """
    return [
        wl_dataframe[
            (wl_dataframe["event_date"] > row["event_date"] - row["data_time_gap"])
            & (wl_dataframe["event_date"] < row["event_date"])
        ]
        for _, row in gaps_dataframe.iterrows()
    ]


def merge_dataframes(
    wl_combined_dataframe: pd.DataFrame, wl_dataframe: pd.DataFrame
) -> pd.DataFrame:
    """
    Fusionne les DataFrames.

    :param wl_combined_dataframe: (pd.DataFrame) DataFrame contenant les données combinées.
    :param wl_dataframe: (pd.DataFrame) DataFrame contenant les données à ajouter.
    :return: (pd.DataFrame) DataFrame contenant les données à ajouter et celles combinées.
    """
    wl_combined_dataframe = wl_combined_dataframe.merge(
        wl_dataframe, on="event_date", how="left", suffixes=("", "_wl")
    )

    wl_combined_dataframe["value"] = wl_combined_dataframe["value"].combine_first(
        wl_combined_dataframe["value_wl"]
    )
    wl_combined_dataframe["time_serie_code"] = wl_combined_dataframe[
        "time_serie_code"
    ].combine_first(wl_combined_dataframe["time_serie_code_wl"])

    return wl_combined_dataframe.drop(columns=["value_wl", "time_serie_code_wl"])


def fill_data_gaps(
    gaps_dataframe: pd.DataFrame,
    wl_dataframe: pd.DataFrame,
    wl_combined_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Permet de remplir les périodes de données manquantes.

    :param gaps_dataframe: (pd.DataFrame[TimeSerieDataSchema]) DataFrame contenant les périodes de données manquantes.
    :param wl_dataframe: (pd.DataFrame[TimeSerieDataSchema]) DataFrame contenant les données à ajouter.
    :param wl_combined_dataframe: (pd.DataFrame[TimeSerieDataSchema]) DataFrame contenant les données combinées.
    :return: (pd.DataFrame[TimeSerieDataSchema]) DataFrame contenant les données ajoutées au données combinées.
    """
    LOGGER.debug(
        f"Remplissage des données manquantes à partir de la série temporelle {wl_dataframe['time_serie_code'].unique()}."
    )

    gaps_dataframe_list: list[pd.DataFrame[TimeSerieDataSchema]] = (
        get_gaps_dataframe_list(
            gaps_dataframe=gaps_dataframe, wl_dataframe=wl_dataframe
        )
    )

    wl_combined_dataframe: pd.DataFrame[TimeSerieDataSchema] = pd.concat(
        [wl_combined_dataframe] + gaps_dataframe_list
    )
    wl_combined_dataframe: pd.DataFrame[TimeSerieDataSchema] = merge_dataframes(
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

    :param wl_combined_dataframe: (pd.DataFrame) DataFrame contenant les données combinées.
    :param gaps_dataframe: (pd.DataFrame) DataFrame contenant les périodes de données manquantes.
    :param wl_dataframe: (pd.DataFrame) DataFrame contenant les données à ajouter aux données combinées.
    :return: (pd.DataFrame[TimeSerieDataSchema]]) Données de niveau d'eau combinées.
    """
    LOGGER.debug(get_data_gaps_message(gaps=gaps_dataframe))

    wl_combined_dataframe: pd.DataFrame[TimeSerieDataSchema] = fill_data_gaps(
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

    :param wl_combined_dataframe: (pd.DataFrame) DataFrame contenant les données de niveau d'eau combinées.
    :param wl_data_dataframe: (pd.DataFrame) DataFrame contenant les données de niveau d'eau.
    :param gaps_dataframe: (pd.DataFrame) DataFrame contenant les périodes de données manquantes.
    :return: (pd.DataFrame) DataFrame contenant les données de niveau d'eau combinées.
    """
    if wl_combined_dataframe.empty:
        return wl_data_dataframe

    return process_gaps_to_fill(
        wl_combined_dataframe=wl_combined_dataframe,
        wl_dataframe=wl_data_dataframe,
        gaps_dataframe=gaps_dataframe,
    )


def get_data_gap_periods(gaps: pd.DataFrame) -> list[DataGapPeriod]:
    """
    Récupère les périodes de données manquantes.

    :param gaps: (pd.DataFrame) DataFrame contenant les périodes de données manquantes.
    :return: (list[DataGap]) Périodes de données manquantes.
    """
    return [
        DataGapPeriod(
            start=row["event_date"] - row["data_time_gap"], end=row["event_date"]
        )
        for index, row in gaps.iterrows()
    ]


def get_data_gaps_message(gaps: pd.DataFrame) -> str:
    """
    Journalise les périodes de données manquantes.

    :param gaps: (pd.DataFrame) Périodes de données manquantes.
    :return: (str) Journalisation des périodes de données manquantes.
    """
    data_gaps_list: list[DataGapPeriod] = get_data_gap_periods(gaps=gaps)

    total_duration_minutes = (
        sum((gap.duration for gap in data_gaps_list), timedelta()).total_seconds() / 60
    )
    gaps_str = "; ".join([str(gap) for gap in data_gaps_list])

    return f"{total_duration_minutes} minutes de données manquantes pour les périodes suivantes : {gaps_str}."


def create_nan_date_row(date_time: str) -> NanDateRow:
    """
    Crée une ligne de données avec une valeur de NaN pour une date donnée.

    :param date_time: (str) Date.
    :return: (NanDateRow) Ligne de données.
    """
    return {"event_date": pd.to_datetime(date_time), "value": np.nan}


def add_nan_date_row(wl_dataframe: pd.DataFrame, time: str) -> pd.DataFrame:
    """
    Ajoute une ligne de données avec une valeur de NaN à partir d'une date.

    :param wl_dataframe: (pd.DataFrame) DataFrame contenant les données.
    :param time: (str) Date.
    :return: (pd.DataFrame) DataFrame contenant la ligne ajouter aux autres données.
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

    :param wl_dataframe: (pd.DataFrame[TimeSerieDataSchema]) Données de la série temporelle.
    :param from_time: (str) Date de début.
    :param to_time: (str) Date de fin.
    :return: (pd.DataFrame[TimeSerieDataSchema]) Données de la série temporelle nettoyées.
    """
    LOGGER.debug(
        "Nettoyage des données de la série temporelle et validation du temps de début et de fin."
    )

    wl_dataframe.dropna(subset=["value"], inplace=True)

    if wl_dataframe["event_date"].iloc[0] > pd.to_datetime(from_time):
        wl_dataframe = add_nan_date_row(wl_dataframe=wl_dataframe, time=from_time)

    if wl_dataframe["event_date"].iloc[-1] < pd.to_datetime(to_time):
        wl_dataframe = add_nan_date_row(wl_dataframe=wl_dataframe, time=to_time)

    return wl_dataframe


def get_time_series_data(
    stations_handler: StationsHandlerProtocol,
    station_id: str,
    from_time: str,
    to_time: str,
    time_serie_code: TimeSeriesProtocol,
    buffer_time: Optional[timedelta] = None,
    qc_flag_filter: Optional[list[str] | None] = None,
) -> pd.DataFrame | None:
    """
    Récupère les données de la série temporelle.

    :param stations_handler: (StationsHandlerProtocol) Gestionnaire des stations.
    :param station_id: (str) Identifiant de la station.
    :param from_time: (str) Date de début.
    :param to_time: (str) Date de fin.
    :param time_serie_code: (TimeSeriesProtocol) Série temporelle.
    :param buffer_time: (Optional[timedelta]) Temps tampon à ajouter au début et à la fin de la période de données.
    :param qc_flag_filter: (Optional[list[str] | None]) Filtre de qualité des données.
    :return: (pd.DataFrame[TimeSerieDataSchema] | None) Données de la série temporelle.
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

    wl_data: pd.DataFrame[TimeSerieDataSchema] = (
        stations_handler.get_time_series_dataframe(
            station=station_id,
            from_time=from_time_buffered,
            to_time=to_time_buffered,
            time_serie_code=time_serie_code,
            qc_flag_filter=qc_flag_filter,
        )
    )

    if wl_data.empty:
        return None

    return clean_time_series_data(
        wl_dataframe=wl_data, from_time=from_time, to_time=to_time
    )


def get_empty_dataframe() -> pd.DataFrame:
    return pd.DataFrame(columns=list(TimeSerieDataSchema.__annotations__.keys()))


def get_datetime_from_iso8601(date: str) -> datetime:
    return datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")


def get_iso8601_from_datetime(date: datetime) -> str:
    return date.strftime("%Y-%m-%dT%H:%M:%SZ")


@retry_tenacity()
def get_water_level_data(
    stations_handler: StationsHandlerProtocol,
    station_id: str,
    from_time: str,
    to_time: str,
    time_series_priority: Collection[TimeSeriesProtocol],
    buffer_time: Optional[timedelta | None] = None,
    max_time_gap: Optional[str | None] = None,
    threshold_interpolation_filling: Optional[str | None] = None,
    qc_flag_filter: Optional[list[str] | None] = None,
) -> pd.DataFrame:
    """
    Récupère et traite les séries temporelles de niveau d'eau pour une station donnée.

    :param stations_handler: (StationsHandlerProtocol) Gestionnaire des stations.
    :param station_id: (str) Identifiant de la station.
    :param from_time: (str) Date de début.
    :param to_time: (str) Date de fin.
    :param time_series_priority: (Collection[TimeSeriesProtocol]) Liste des séries temporelles à récupérer en ordre de priorité.
    :param buffer_time: (Optional[timedelta | None]) Temps tampon à ajouter au début et à la fin de la période de données.

    :param max_time_gap: (Optional[str | None]) Intervalle de temps maximal permis. Si None, l'interpolation et le remplissage
                                                des données manquantes est désactivée.
    :param threshold_interpolation_filling: (Optional[str | None]) Seuil de temps en dessous duquel les données manquantes
                                                    sont interpolées ou remplies. Si None, les données manquantes sont
                                                    seulement remplies par la time série suivante.
    :param qc_flag_filter: (Optional[list[str] | None]) Filtre de qualité des données.
    :return: (pd.DataFrame[TimeSerieDataSchema]) Données de niveau d'eau combinées.
    """
    wl_combined: pd.DataFrame = get_empty_dataframe()

    for index, time_serie in enumerate(time_series_priority):
        wl_data: pd.DataFrame[TimeSerieDataSchema] = get_time_series_data(
            stations_handler=stations_handler,
            station_id=station_id,
            from_time=from_time,
            to_time=to_time,
            time_serie_code=time_serie,
            buffer_time=buffer_time,
            qc_flag_filter=qc_flag_filter,
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

        wl_data: pd.DataFrame[TimeSerieDataSchema] = process_gaps_to_interpolate(
            wl_dataframe=wl_data,
            max_time_gap=max_time_gap,
            threshold_interpolation_filling=threshold_interpolation_filling,
        )

        # todo : identifier les données manquantes après interpolation ?

        wl_combined: pd.DataFrame[TimeSerieDataSchema] = combine_water_level_data(
            wl_combined_dataframe=wl_combined,
            wl_data_dataframe=wl_data,
            gaps_dataframe=gaps_to_fill,
        )

    else:
        LOGGER.debug(
            f"Toutes les séries temporelles disponibles pour la station {station_id} ont été traitées: {time_series_priority}."
        )

    return wl_combined


# todo isTidal == False  -> interpolation linéaire plutôt que spline cubique ?
# todo problème avec l'interpolation même avec le buffer_time si les données sont manquantes à la fin
#  ou au début de la période NaN
# todo valider le holding avant de demander les données ! -> sinon refaire les polygon sans cette station ?
