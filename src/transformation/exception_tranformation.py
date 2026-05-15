"""
Module contenant les exceptions liées à la transformation des données.

Ce module contient les classes d'exceptions qui sont levées lors de la transformation des données.
"""

from dataclasses import dataclass

import i18n


@dataclass(frozen=True)
class WaterLevelDataRequiredError(Exception):
    """
    Exception levée lorsqu'il manque les données de niveau d'eau.
    """

    def __str__(self):
        return i18n.t("transformation.exception_tranformation.water_level_required")
