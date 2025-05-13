"""
Module pour les modèles pour les filtres.

Ce module contient les modèles de données pour les filtres des données.
"""

from enum import StrEnum
from typing import Protocol, Optional

from schema import Status


class DataFilterConfigProtocol(Protocol):
    """
    Protocole pour la configuration des filtres de données.

    :param min_latitude: (int | float) La latitude minimale.
    :param max_latitude: (int | float) La latitude maximale.
    :param min_longitude: (int | float) La longitude minimale.
    :param max_longitude: (int | float) La longitude maximale.
    :param min_depth: (int | float) La profondeur minimale.
    :param max_depth: (Optional[int | float]) La profonde maximale.
    :param min_speed: (Optional[int | float]) La vitesse minimale.
    :param max_speed: (Optional[int | float]) La vitesse maximale.
    """

    min_latitude: int | float
    """La latitude minimale."""
    max_latitude: int | float
    """La latitude maximale."""
    min_longitude: int | float
    """La longitude minimale."""
    max_longitude: int | float
    """La longitude maximale."""
    min_depth: int | float
    """La profondeur minimale."""
    max_depth: Optional[int | float]
    """La profondeur maximale."""
    min_speed: Optional[int | float]
    """La vitesse minimale."""
    max_speed: Optional[int | float]
    """La vitesse maximale."""
    filter_to_apply: list[str]
    """Les filtres à appliquer."""


class FiltersEnum(StrEnum):
    """
    Enum for status codes.
    """

    SPEED_FILTER = "SPEED_FILTER"
    LATITUDE_FILTER = "LATITUDE_FILTER"
    LONGITUDE_FILTER = "LONGITUDE_FILTER"
    TIME_FILTER = "TIME_FILTER"
    DEPTH_FILTER = "DEPTH_FILTER"


FILTER_STATUS_MAPPING: dict[FiltersEnum, Status] = {
    FiltersEnum.SPEED_FILTER: Status.REJECTED_BY_SPEED_FILTER,
    FiltersEnum.LATITUDE_FILTER: Status.REJECTED_BY_LATITUDE_FILTER,
    FiltersEnum.LONGITUDE_FILTER: Status.REJECTED_BY_LONGITUDE_FILTER,
    FiltersEnum.TIME_FILTER: Status.REJECTED_BY_TIME_FILTER,
    FiltersEnum.DEPTH_FILTER: Status.REJECTED_BY_DEPTH_FILTER,
}
