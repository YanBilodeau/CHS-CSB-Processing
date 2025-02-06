"""
Module pour les modèles de métadonnées.

Ce module contient les modèles de métadonnées pour les données du CSB.
"""

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Collection

from loguru import logger

from .order.order_models import IHOorderQualifiquation

LOGGER = logger.bind(name="CSB-Processing.Metadata.Models")


REDUCTION_METHOD = "The dataset has been reduced to CD thanks to predicted tides pulled from IWLS at the following stations: {stations}."
"""Méthode de réduction du niveau d'eau"""
NO_TIDE_STATIONS = "The dataset has not been reduced to CD."
"""Pas de stations de marée"""


@dataclass
class CSBmetadata:
    """
    Classe pour les métadonnées des données du CSB.
    """

    start_date: datetime
    """Date de début"""
    end_date: datetime
    """Date de fin"""
    vessel: str
    """Identifiant et nom du navire"""
    sounding_hardware: str
    """Matériel de sondage"""
    soundding_technique: str
    """Technique de sondage"""
    sounder_draft: float
    """Tirant d'eau du sondeur"""
    tvu: float
    """Invertitude verticale"""
    thu: float
    """Invertitude horizontale"""
    sotfware_version: str = field(repr=False, metadata={"exclude": True})
    """Version du logiciel"""
    tide_stations: Collection[str] = field(repr=False, metadata={"exclude": True})
    """Stations de marée"""
    water_Level_reduction_method: str = field(init=False)
    """Méthode de réduction du niveau d'eau"""
    positioning_method: str = "WAAS"
    """Méthode de positionnement"""
    resolution: str = "Point Cloud"
    """Résolution des données"""
    data_processing_software: str = "CHS-CSB-Processing {version}"
    """Logiciel de traitement des données"""
    horizontal_coordinate_reference_system: str = "WGS 84 - EPSG:4326"
    """Système de coordonnées horizontal"""
    vertical_coordinate_reference_system: str = "Chart Datum"
    """Système de coordonnées vertical"""
    iho_order_statistic: IHOorderQualifiquation = None
    """Statistiques des ordre IHO"""

    def __post_init__(self):
        """
        Méthode pour initialiser les valeurs par défaut.
        """
        self.data_processing_software = self.data_processing_software.format(
            version=self.sotfware_version
        )

        self.water_Level_reduction_method = (
            REDUCTION_METHOD.format(stations=", ".join(self.tide_stations))
            if self.tide_stations
            else NO_TIDE_STATIONS
        )

    def to_dict(self) -> dict:
        """
        Méthode pour convertir les métadonnées en dictionnaire.

        :return: Dictionnaire des métadonnées.
        :rtype: dict
        """
        LOGGER.debug("Conversion des métadonnées en dictionnaire.")

        result = {}
        for key, value in asdict(self).items():
            if not self.__dataclass_fields__[key].metadata.get("exclude", False):
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                else:
                    result[key] = value

        return result
