"""
Module pour les modèles de transformation.

Ce module contient les modèles de données pour la transformation des données.
"""

from datetime import datetime
from typing import Protocol


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
