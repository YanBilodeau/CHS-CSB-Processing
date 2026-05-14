"""
Module définissant le contexte de traitement des données CSB.

Ce module expose :class:`ProcessingContext`, un objet léger créé une seule fois dans
``processing_workflow`` et propagé en un unique paramètre à ``georeference_bathymetry``,
``export_metadata`` et ``CSBmetadata``, afin d'éviter la propagation de paramètres épars
(``datalogger_type``, ``already_at_chart_datum``) à travers plusieurs niveaux d'appel.
"""

from dataclasses import dataclass, field
from typing import Optional

from ingestion import DataLoggerType


@dataclass
class ProcessingContext:
    """
    Contexte de traitement d'une acquisition CSB.

    Regroupe les propriétés caractérisant l'acquisition de la donnée
    (type de capteur, statut de réduction au zéro des cartes) et expose
    des méthodes de résolution des constantes d'incertitude.

    Exemple d'utilisation typique dans ``processing_workflow`` ::

        ctx = ProcessingContext(
            datalogger_type=datalogger_type,
            already_at_chart_datum=already_at_chart_datum,
        )
        georeference_bathymetry(..., processing_context=ctx)
        export_processed_data_and_metadata(..., processing_context=ctx)
    """

    datalogger_type: Optional[DataLoggerType] = field(default=None)
    """Type de capteur (valeur de :class:`~ingestion.DataLoggerType`)."""
    already_at_chart_datum: bool = field(default=False)
    """``True`` si les données sont déjà réduites au zéro des cartes."""

    def resolve_constant_thu(self, default: float) -> float:
        """
        Retourne la constante THU à appliquer.

        Interroge ``datalogger_uncertainty.json``. Si le type est absent du JSON,
        retourne *default* (valeur issue du TOML).

        :param default: Valeur par défaut de la constante THU.
        :type default: float
        :return: Constante THU effective.
        :rtype: float
        """
        from transformation.uncertainty.compute_tpu import (
            get_constant_thu_for_datalogger,
        )

        return get_constant_thu_for_datalogger(self.datalogger_type, default)

    def resolve_constant_tvu(self, default: float) -> float:
        """
        Retourne la constante TVU à appliquer quand ``already_at_chart_datum=True``.

        Interroge ``datalogger_uncertainty.json``. Si le type est absent, retourne *default*.
        Retourne *default* sans interroger le JSON si ``already_at_chart_datum=False``.

        :param default: Valeur par défaut (0 par convention).
        :type default: float
        :return: Constante TVU effective.
        :rtype: float
        """
        if not self.already_at_chart_datum:
            return default

        from transformation.uncertainty.compute_tpu import (
            get_constant_tvu_for_datalogger,
        )

        return get_constant_tvu_for_datalogger(self.datalogger_type, default)

    def resolve_sounder_draft(self, sounder, waterline) -> float | str:
        """
        Retourne le tirant d'eau du sondeur.

        Retourne ``None`` si les données sont déjà au zéro des cartes
        (tirant d'eau non applicable).

        :param sounder: Capteur sondeur (attribut ``.z`` requis).
        :param waterline: Ligne d'eau (attribut ``.z`` requis).
        :return: Tirant d'eau en mètres ou "N/A" si les données sont déjà au zéro des cartes.
        :rtype: float | str
        """
        if self.already_at_chart_datum:
            return "N/A"

        return sounder.z - waterline.z
