"""
Module pour les modèles de transformation.

Ce module contient les modèles de données pour la transformation des données.
"""

from datetime import datetime
from typing import Protocol, Optional


class DataFilterConfigProtocol(Protocol):
    """
    Protocole pour la configuration des filtres de données.

    :param min_latitude: (int | float) La latitude minimale.
    :param max_latitude: (int | float) La latitude maximale.
    :param min_longitude: (int | float) La longitude minimale.
    :param max_longitude: (int | float) La longitude maximale.
    :param min_depth: (int | float) La profondeur minimale.
    :param max_depth: (Optional[int | float]) La profonde maximale.
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


class SensorProtocol(Protocol):
    """
    Protocole pour les données pour un capteur.

    :param time_stamp: Date et heure.
    :type time_stamp: datetime
    :param x: Bras de levier X.
    :type x: float
    :param y: Bras de levier Y.
    :type y: float
    :param z: Bras de levier Z.
    :type z: float
    """

    time_stamp: datetime
    """Date et heure."""
    x: float
    """Bras de levier X."""
    y: float
    """Bras de levier Y."""
    z: float
    """Bras de levier Z."""


class WaterlineProtocol(Protocol):
    """
    Protocole pour les données pour une ligne d'eau.

    :param time_stamp: Date et heure.
    :type time_stamp: datetime
    :param z: Bras de levier Z.
    :type z: float
    """

    time_stamp: datetime
    """Date et heure."""
    z: float
    """Bras de levier Z."""
