from datetime import timedelta
from functools import partial

from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    before_log,
    retry_if_exception_type,
)

from .exception_time_serie import InterpolationValueError

LOGGER = logger.bind(name="CSB-Pipeline.TimeSerie.Retry")


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
interpolation_retry = partial(
    retry,
    stop=stop_after_attempt(1),
    wait=wait_exponential_jitter(initial=1, jitter=1, max=3),
    before=before_log(LOGGER, LEVEL),  # type: ignore
    after=double_buffer_time,
    retry=retry_if_exception_type(InterpolationValueError),
)