"""
Module contenant les exceptions liées aux filtres des données.

Ce module contient les classes d'exceptions qui sont levées lors du filtrage des données.
"""

from dataclasses import dataclass

import i18n


@dataclass(frozen=True)
class DataCleaningFunctionError(Exception):
    """
    Exception levée lorsqu'une fonction de nettoyage n'existe pas.

    :param function: (str) La fonction de nettoyage.
    """

    function: str
    """La fonction de nettoyage."""

    def __str__(self):
        return i18n.t(
            "filter.exception_filter.error_function_not_found", function=self.function
        )
