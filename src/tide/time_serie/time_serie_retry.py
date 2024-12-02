"""
Module pour la gestion des tentatives d'interpolation de séries temporelles.

Ce module contient les fonctions pour gérer les tentatives d'interpolation de séries temporelles.
"""

from datetime import timedelta
from functools import partial

from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    before_log,
    retry_if_exception_type,
    RetryCallState,
)

from .exception_time_serie import InterpolationValueError
from ..voronoi.voronoi_models import TimeSeriesProtocol

LOGGER = logger.bind(name="CSB-Pipeline.TimeSerie.Retry")


def double_buffer_time(retry_state: RetryCallState) -> None:
    """
    Fonction pour doubler le temps tampon pour la prochaine tentative d'interpolation.

    :param retry_state: État de la tentative.
    :type retry_state: RetryCallState
    """
    buffer_time: timedelta = retry_state.kwargs.get("buffer_time")

    if buffer_time is None:
        buffer_time = timedelta(hours=24)

    LOGGER.debug(
        f"Augmentation du temps tampon pour la prochaine tentative d'interpolation de "
        f"{retry_state.kwargs.get('buffer_time')} à {buffer_time * 2}."
    )

    retry_state.kwargs["buffer_time"] = buffer_time * 2


def exclude_time_serie_retry(retry_state: RetryCallState) -> None:
    """
    Fonction pour exclure les tentatives d'interpolation de séries temporelles.

    :param retry_state: État de la tentative.
    :type retry_state: RetryCallState
    """
    from .time_serie_dataframe import get_water_level_data

    error: InterpolationValueError = retry_state.outcome.exception()

    time_series: list[TimeSeriesProtocol] = retry_state.kwargs.setdefault(
        "time_series_excluded_from_interpolation", []
    )
    time_series.append(error.time_serie)

    kwargs: dict = {
        key: value
        for key, value in retry_state.kwargs.items()
        if key != "time_series_excluded_from_interpolation"
    }

    get_water_level_data(**kwargs, time_series_excluded_from_interpolation=time_series)


LEVEL: str = "TRACE"
interpolation_retry = partial(
    retry,
    stop=stop_after_attempt(5),
    wait=wait_exponential_jitter(initial=1, jitter=1, max=3),
    before=before_log(LOGGER, LEVEL),  # type: ignore
    after=double_buffer_time,
    retry=retry_if_exception_type(InterpolationValueError),
    retry_error_callback=exclude_time_serie_retry,
)
