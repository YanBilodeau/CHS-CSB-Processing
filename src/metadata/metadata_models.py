"""
Module pour les modèles de métadonnées.

Ce module contient les modèles de métadonnées pour les données du CSB.
"""

from dataclasses import dataclass, field
from typing import Collection, Optional

from loguru import logger

from ingestion import DataLoggerType
from .order.order_models import IHOorderQualifiquation

LOGGER = logger.bind(name="CSB-Processing.Metadata.Models")


REDUCTION_METHOD = "The dataset has been reduced to CD thanks to water level pulled from IWLS at the following stations: {stations}."
"""Méthode de réduction du niveau d'eau"""
NO_TIDE_STATIONS = "The dataset has not been reduced to CD."
"""Pas de stations de marée"""
ALREADY_AT_CHART_DATUM = "The dataset was provided already reduced to Chart Datum. No water level reduction was applied."
"""Données déjà au zéro des cartes"""
CHART_DATUM = "Chart Datum"
"""Niveau de référence des cartes"""

DEFAULT_POSITIONING_METHOD: str = "Wide Area Augmentation System (WAAS)"
"""Méthode de positionnement par défaut."""

POSITIONING_METHOD_BY_DATALOGGER: dict[DataLoggerType, str] = {
    DataLoggerType.HYDROBLOCK: "Precise Point Positioning (PPP)",
}
"""Correspondance DataLoggerType → méthode de positionnement.
Contient uniquement les types dont la méthode diffère de DEFAULT_POSITIONING_METHOD."""


def get_positioning_method(datalogger_type: DataLoggerType) -> str:
    """
    Retourne la méthode de positionnement associée au type de capteur.

    Retourne ``DEFAULT_POSITIONING_METHOD`` si le type n'est pas présent dans
    ``POSITIONING_METHOD_BY_DATALOGGER``.

    :param datalogger_type: Type de capteur.
    :type datalogger_type: DataLoggerType
    :return: Méthode de positionnement.
    :rtype: str
    """
    return POSITIONING_METHOD_BY_DATALOGGER.get(
        datalogger_type, DEFAULT_POSITIONING_METHOD
    )


@dataclass
class CSBmetadata:
    """
    Classe pour les métadonnées des données du CSB.
    """

    start_date: str
    """Date de début"""
    end_date: str
    """Date de fin"""
    vessel: str
    """Identifiant et nom du navire"""
    sounding_hardware: str
    """Matériel de sondage"""
    sounding_technique: str
    """Technique de sondage"""
    sounder_draft: Optional[float]
    """Tirant d'eau du sondeur (None si les données sont déjà au zéro des cartes)"""
    tvu: float
    """Incertitude verticale"""
    thu: float
    """Incertitude horizontale"""
    sotfware_version: str = field(repr=False, metadata={"exclude": True})
    """Version du logiciel"""
    tide_stations: Collection[str] = field(repr=False, metadata={"exclude": True})
    """Stations de marée"""
    vertical_coordinate_reference_system: str = field(init=False)
    """Système de coordonnées vertical"""
    water_Level_reduction_method: str = field(init=False)
    """Méthode de réduction du niveau d'eau"""
    positioning_method: str = DEFAULT_POSITIONING_METHOD
    """Méthode de positionnement"""
    resolution: str = "Point Cloud"
    """Résolution des données"""
    horizontal_coordinate_reference_system: str = "WGS 84 - EPSG:4326"
    """Système de coordonnées horizontal"""
    data_processing_software: str = "CHS-CSB-Processing {version}"
    """Logiciel de traitement des données"""
    already_at_chart_datum: bool = False
    """Les données sont déjà réduites au zéro des cartes"""
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
            else (
                ALREADY_AT_CHART_DATUM
                if self.already_at_chart_datum
                else NO_TIDE_STATIONS
            )
        )

        self.vertical_coordinate_reference_system = (
            CHART_DATUM if (self.tide_stations or self.already_at_chart_datum) else None
        )

    def __dict__(self) -> dict:
        """
        Convertit les données en un dictionnaire.
        """
        return {
            "Start Date": self.start_date,
            "End Date": self.end_date,
            "Vessel": self.vessel,
            "Horizontal Coordinate Reference System": self.horizontal_coordinate_reference_system,
            "Vertical Coordinate Reference System": self.vertical_coordinate_reference_system,
            "Sounding Hardware": self.sounding_hardware,
            "Sounding Technique": self.sounding_technique,
            "Positioning Method": self.positioning_method,
            "Sounder Draft (m)": self.sounder_draft,
            "TVU (m)": self.tvu,
            "THU (m)": self.thu,
            "Water Level Reduction Method": self.water_Level_reduction_method,
            "Resolution": self.resolution,
            "Data Processing Software": self.data_processing_software,
            "IHO Order Statistic": self.iho_order_statistic.__dict__(),
        }
