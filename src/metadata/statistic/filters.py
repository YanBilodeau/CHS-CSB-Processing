"""
Filtres pour nettoyage de données de sondage.

Ce module implémente le pattern Strategy pour permettre l'extension
de filtres sans modifier le code existant (Open/Closed Principle).
"""

from abc import ABC, abstractmethod

import geopandas as gpd
import pandas as pd


class Filter(ABC):
    """
    Protocole abstrait pour les filtres de GeoDataFrame.

    Implémente le principe Open/Closed : nouvelles implémentations
    par héritage sans modifier ce code.
    """

    @abstractmethod
    def apply(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Applique le filtre au GeoDataFrame.

        :param gdf: GeoDataFrame source.
        :type gdf: gpd.GeoDataFrame
        :return: GeoDataFrame filtré.
        :rtype: gpd.GeoDataFrame
        """
        ...


class DeltatimeFilter(Filter):
    """
    Filtre par seuil de deltatime.

    Exclut les points dont le deltatime dépasse le seuil,
    mais conserve toujours les NaT (premiers points).
    """

    def __init__(self, threshold: pd.Timedelta, col: str = "deltatime"):
        """
        Initialise le filtre de deltatime.

        :param threshold: Seuil maximal accepté.
        :type threshold: pd.Timedelta
        :param col: Nom de la colonne deltatime.
        :type col: str
        """
        self.threshold = threshold
        self.col = col

    def apply(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Applique le filtre de deltatime.

        :param gdf: GeoDataFrame avec colonne deltatime.
        :type gdf: gpd.GeoDataFrame
        :return: GeoDataFrame filtré.
        :rtype: gpd.GeoDataFrame
        :raises KeyError: Si la colonne deltatime est absente.
        """
        if self.col not in gdf.columns:
            raise KeyError(
                f"Colonne '{self.col}' introuvable. "
                f"Appelez d'abord add_deltatime_column()."
            )

        mask = gdf[self.col].isna() | (gdf[self.col] <= self.threshold)
        return gdf[mask].copy()


def apply_filters(gdf: gpd.GeoDataFrame, filters: list[Filter]) -> gpd.GeoDataFrame:
    """
    Applique une liste de filtres séquentiellement.

    :param gdf: GeoDataFrame source.
    :type gdf: gpd.GeoDataFrame
    :param filters: Liste de filtres à appliquer dans l'ordre.
    :type filters: list[Filter]
    :return: GeoDataFrame filtré.
    :rtype: gpd.GeoDataFrame
    """
    result = gdf
    for filter_obj in filters:
        result = filter_obj.apply(result)

    return result
