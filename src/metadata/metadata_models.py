"""
Module pour les modèles de métadonnées.

Ce module contient les modèles de métadonnées pour les données du CSB.
"""

from dataclasses import dataclass, field
from typing import Collection, Optional

import i18n
from loguru import logger

from ingestion import DataLoggerType
from .order.order_models import IHOorderQualifiquation
from processing_context import ProcessingContext

LOGGER = logger.bind(name="CSB-Processing.Metadata.Models")

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

    Retourne la méthode par défaut si le type n'est pas présent dans le mapping.

    :param datalogger_type: Type de capteur.
    :type datalogger_type: DataLoggerType
    :return: Méthode de positionnement.
    :rtype: str
    """
    if datalogger_type == DataLoggerType.HYDROBLOCK:
        return i18n.t("metadata.metadata_models.positioning_method_hydroblock")

    return i18n.t("metadata.metadata_models.default_positioning_method")


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
    already_at_chart_datum: bool = field(init=False, default=False)
    """Les données sont déjà réduites au zéro des cartes (dérivé de processing_context)"""
    positioning_method: str = field(
        default_factory=lambda: i18n.t(
            "metadata.metadata_models.default_positioning_method"
        )
    )
    """Méthode de positionnement"""
    resolution: str = "Point Cloud"
    """Résolution des données"""
    horizontal_coordinate_reference_system: str = "WGS 84 - EPSG:4326"
    """Système de coordonnées horizontal"""
    data_processing_software: str = "CHS-CSB-Processing {version}"
    """Logiciel de traitement des données"""
    processing_context: Optional[ProcessingContext] = field(default=None, repr=False)
    """Contexte de traitement (type de capteur, statut de réduction au zéro des cartes)"""
    iho_order_statistic: IHOorderQualifiquation = None
    """Statistiques des ordre IHO"""

    def __post_init__(self):
        """
        Méthode pour initialiser les valeurs par défaut.
        """
        self.already_at_chart_datum = (
            self.processing_context.already_at_chart_datum
            if self.processing_context is not None
            else False
        )

        self.data_processing_software = self.data_processing_software.format(
            version=self.sotfware_version
        )

        self.water_Level_reduction_method = (
            i18n.t(
                "metadata.metadata_models.reduction_method",
                stations=", ".join(self.tide_stations),
            )
            if self.tide_stations
            else (
                i18n.t("metadata.metadata_models.already_at_chart_datum")
                if self.already_at_chart_datum
                else i18n.t("metadata.metadata_models.no_tide_stations")
            )
        )

        self.vertical_coordinate_reference_system = (
            i18n.t("metadata.metadata_models.chart_datum")
            if (self.tide_stations or self.already_at_chart_datum)
            else None
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
