"""
Module contenant les exceptions liées à la transformation des données.

Ce module contient les classes d'exceptions qui sont levées lors de la transformation des données.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DataCleaningFunctionError(Exception):
    """
    Exception levée lorsqu'une fonction de nettoyage n'existe pas.

    :param function: (str) La fonction de nettoyage.
    """

    function: str
    """La fonction de nettoyage."""

    def __str__(self):
        return f"La fonction de nettoyage '{self.function}' n'existe pas."


@dataclass(frozen=True)
class WaterLevelDataRequiredError(Exception):
    """
    Exception levée lorsqu'il manque les données de niveau d'eau.
    """

    def __str__(self):
        return "Les données de niveau d'eau sont requises pour effectuer le géoréférencement."
