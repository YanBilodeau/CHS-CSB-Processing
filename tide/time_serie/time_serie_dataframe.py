from datetime import timedelta
from typing import Optional, Any, Collection

import numpy as np
import pandas as pd
from loguru import logger

from .time_serie_models import (
    DataGapPeriod,
    TimeSeriesProtocol,
    StationsHandlerProtocol,
)
from ..schema import TimeSerieDataSchema, validate_schema

LOGGER = logger.bind(name="CSB-Pipeline.TimeSerie")

NanDateRow = dict[str, Any]


def create_nan_date_row(date_time: str) -> NanDateRow:
    """
    Crée une ligne de données avec une valeur de NaN pour une date donnée.

    :param date_time: (str) Date.
    :return: (NanDateRow) Ligne de données.
    """
    return {"event_date": pd.to_datetime(date_time), "value": np.nan}


def add_nan_date_row(wl_data: pd.DataFrame, time: str) -> pd.DataFrame:
    """
    Ajoute une ligne de données avec une valeur de NaN à partir d'une date.

    :param wl_data: (pd.DataFrame) DataFrame contenant les données.
    :param time: (str) Date.
    :return: (pd.DataFrame) DataFrame contenant la ligne ajouter aux autres données.
    """
    LOGGER.debug(f"Ajout d'une ligne de données NaN à partir de la date '{time}'.")

    wl_data.loc[len(wl_data)] = create_nan_date_row(date_time=time)
    wl_data.sort_values(by="event_date", inplace=True)
    wl_data.reset_index(drop=True, inplace=True)

    return wl_data


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


def identify_data_gaps(
    wl_dataframe: pd.DataFrame, max_time_gap: str
) -> pd.DataFrame:
    """
    Identifie les périodes de données manquantes.

    :param wl_dataframe: (pd.DataFrame[TimeSerieDataSchema]) DataFrame contenant les données.
    :param max_time_gap: (str) Intervalle de temps pour combler les données manquantes.
    :return: (pd.DataFrame[TimeSerieDataSchema]) Périodes de données manquantes.
    """
    LOGGER.debug(
        f"Identification des périodes de données manquantes de plus de {max_time_gap}."
    )

    first_row, last_row = get_first_and_last_rows(wl_dataframe=wl_dataframe)

    non_nan_dataframe: pd.DataFrame = wl_dataframe.dropna(subset=["value"])
    non_nan_dataframe = extend_rows_to_deltatime(
        non_nan_dataframe=non_nan_dataframe, first_row=first_row, last_row=last_row
    )
    non_nan_dataframe.sort_values(by="event_date", inplace=True)
    non_nan_dataframe.reset_index(drop=True, inplace=True)
    non_nan_dataframe["data_time_gap"] = non_nan_dataframe["event_date"].diff()

    gaps_dataframe: pd.DataFrame[TimeSerieDataSchema] = non_nan_dataframe[
        non_nan_dataframe["data_time_gap"] > pd.Timedelta(max_time_gap)
    ]

    return gaps_dataframe


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


def get_data_gap_periods(gaps: pd.DataFrame) -> list[DataGapPeriod]:
    """
    Récupère les périodes de données manquantes.

    :param gaps: (pd.DataFrame) DataFrame contenant les périodes de données manquantes.
    :return: (list[DataGap]) Périodes de données manquantes.
    """
    LOGGER.debug("Récupération des périodes de données manquantes.")

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


def clean_time_series_data(
    wl_data: pd.DataFrame,
    from_time: str,
    to_time: str,
) -> pd.DataFrame:
    """
    Nettoie les données de la série temporelle.

    :param wl_data: (pd.DataFrame[TimeSerieDataSchema]) Données de la série temporelle.
    :param from_time: (str) Date de début.
    :param to_time: (str) Date de fin.
    :return: (pd.DataFrame[TimeSerieDataSchema]) Données de la série temporelle nettoyées.
    """
    LOGGER.debug(
        "Nettoyage des données de la série temporelle et validation du temps de début et de fin."
    )

    wl_data.dropna(subset=["value"], inplace=True)

    if wl_data["event_date"].iloc[0] != pd.to_datetime(from_time):
        wl_data = add_nan_date_row(wl_data=wl_data, time=from_time)

    if wl_data["event_date"].iloc[-1] != pd.to_datetime(to_time):
        wl_data = add_nan_date_row(wl_data=wl_data, time=to_time)

    return wl_data


def get_time_series_data(
    stations_handler: StationsHandlerProtocol,
    station_id: str,
    from_time: str,
    to_time: str,
    time_serie_code: TimeSeriesProtocol,
) -> pd.DataFrame | None:
    """
    Récupère les données de la série temporelle.

    :param stations_handler: (StationsHandlerProtocol) Gestionnaire des stations.
    :param station_id: (str) Identifiant de la station.
    :param from_time: (str) Date de début.
    :param to_time: (str) Date de fin.
    :param time_serie_code: (TimeSeriesProtocol) Série temporelle.
    :return: (pd.DataFrame[TimeSerieDataSchema] | None) Données de la série temporelle.
    """
    wl_data: pd.DataFrame[TimeSerieDataSchema] = (
        stations_handler.get_time_series_dataframe(
            station=station_id,
            from_time=from_time,
            to_time=to_time,
            time_serie_code=time_serie_code,
        )
    )

    if wl_data.empty:
        return None

    validate_schema(wl_data, TimeSerieDataSchema)

    return clean_time_series_data(wl_data=wl_data, from_time=from_time, to_time=to_time)


def process_gaps(
    wl_combined: pd.DataFrame,
    max_time_gap: str,
    wl_data: Optional[pd.DataFrame] = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Identifie et comble les données manquantes.

    :param wl_combined: (pd.DataFrame) DataFrame contenant les données combinées.
    :param wl_data: (pd.DataFrame) DataFrame contenant les données.
    :param max_time_gap: (str) Intervalle de temps maximal permis.
    :return: (tuple[pd.DataFrame[TimeSerieDataSchema], pd.DataFrame[TimeSerieDataSchema]]) Données de la série
                                temporelle combinées et les périodes de données manquantes.
    """

    gaps: pd.DataFrame[TimeSerieDataSchema] = identify_data_gaps(
        wl_dataframe=wl_combined,
        max_time_gap=max_time_gap,
    )

    if gaps.empty:
        return wl_combined, gaps

    LOGGER.debug(get_data_gaps_message(gaps=gaps))

    if wl_data is None:
        return wl_combined, gaps

    wl_combined: pd.DataFrame[TimeSerieDataSchema] = fill_data_gaps(
        gaps_dataframe=gaps,
        wl_dataframe=wl_data,
        wl_combined_dataframe=wl_combined,
    )

    wl_combined.sort_values(by="event_date", inplace=True)
    wl_combined.reset_index(drop=True, inplace=True)

    return wl_combined, gaps


def get_water_level_data(
    stations_handler: StationsHandlerProtocol,
    station_id: str,
    from_time: str,
    to_time: str,
    time_series_priority: Collection[TimeSeriesProtocol],
    max_time_gap: str | None,
) -> pd.DataFrame:
    """
    Récupère et traite les séries temporelles de niveau d'eau pour une station donnée.

    :param stations_handler: (StationsHandlerProtocol) Gestionnaire des stations.
    :param station_id: (str) Identifiant de la station.
    :param from_time: (str) Date de début.
    :param to_time: (str) Date de fin.
    :param time_series_priority: (Collection[TimeSeriesProtocol]) Liste des séries temporelles à récupérer en ordre de priorité.
    :param max_time_gap: (str | None) Intervalle de temps maximal permis.
    :return: (pd.DataFrame[TimeSerieDataSchema]) Données de niveau d'eau combinées.
    """

    def get_empty_dataframe() -> pd.DataFrame:
        return pd.DataFrame(columns=list(TimeSerieDataSchema.__annotations__.keys()))

    wl_combined: pd.DataFrame = get_empty_dataframe()

    for index, time_serie in enumerate(time_series_priority):
        wl_data: pd.DataFrame[TimeSerieDataSchema] = get_time_series_data(
            stations_handler=stations_handler,
            station_id=station_id,
            from_time=from_time,
            to_time=to_time,
            time_serie_code=time_serie,
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

        wl_combined, gaps = process_gaps(
            wl_combined=wl_data if wl_combined.empty else wl_combined,
            wl_data=wl_data if index != 0 else None,
            max_time_gap=max_time_gap,
        )
        if gaps.empty:
            LOGGER.debug(
                f"Aucune donnée manquante pour la station {station_id} avec les séries temporelles: {time_series_priority[:index + 1]}."
            )
            break

    else:
        LOGGER.debug(
            f"Toutes les séries temporelles disponibles pour la station {station_id} ont été traitées: {time_series_priority}."
        )

    return wl_combined
