"""
Module pour les modèles pour les filtres.

Ce module contient les modèles de données pour les filtres des données.
"""

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
