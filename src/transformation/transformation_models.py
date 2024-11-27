"""
Module pour les modèles de transformation.

Ce module contient les modèles de données pour la transformation des données.
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
    """

    min_latitude: int | float
    max_latitude: int | float
    min_longitude: int | float
    max_longitude: int | float
    min_depth: int | float
    max_depth: Optional[int | float]
