"""
Module qui contient les modèles et les protocoles pour manipuler les données des séries temporelles et des stations.
"""

from typing import Protocol, Collection, Optional

import geopandas as gpd


class TimeSeriesProtocol(Protocol):
    """
    Protocole pour définir les types des séries temporelles.
    """

    WLO: str = "wlo"
    """Water Level Observed."""
    WLF_SPINE: str = "wlf-spine"
    """Water Level Forecast Spine."""
    WLF_VTG: str = "wlf-vtg"
    """Water Level Forecast VTG."""
    WLF: str = "wlf"
    """Water Level Forecast."""
    WLP: str = "wlp"
    """Water Level Prediction."""

    def from_str(cls, value: str) -> "TimeSeriesProtocol":
        """
        Méthode pour convertir une chaîne de caractères en série temporelle.

        :param value: Chaîne de caractères.
        :type value: str
        :return: Série temporelle.
        :rtype: TimeSeriesProtocol
        """
        pass


class StationsHandlerProtocol(Protocol):
    """
    Protocole pour définir les méthodes de manipulation des stations.
    """

    def get_stations_geodataframe(
        self,
        filter_time_series: Collection[TimeSeriesProtocol] | None,
        excluded_stations: Collection[str] | None,
        ttl: Optional[int],
    ) -> gpd.GeoDataFrame:
        """
        Méthode pour récupérer le GeoDataFrame des stations.

        :param filter_time_series: Liste des séries temporelles pour filtrer les stations. Si None, toutes les stations sont retournées.
        :type filter_time_series: Collection[TimeSeriesProtocol] | None
        :param excluded_stations: Liste des stations à exclure.
        :type excluded_stations: Collection[str] | None
        :param ttl: Durée de vie du cache.
        :type ttl: Optional[int]
        :return: GeoDataFrame des stations.
        :rtype: gpd.GeoDataFrame
        """
        pass

    def get_stations_geodataframe_from_codes(
        self,
        station_codes: Collection[str],
        filter_time_series: Collection[TimeSeriesProtocol],
    ) -> gpd.GeoDataFrame:
        """
        Méthode pour récupérer le GeoDataFrame d'une station spécifique.

        :param station_codes: Liste des codes des stations.
        :type station_codes: Collection[str]
        :param filter_time_series: Liste des séries temporelles pour filtrer la station.
        :type filter_time_series: Collection[TimeSeriesProtocol]
        :return: GeoDataFrame de la station.
        :rtype: gpd.GeoDataFrame
        """
        pass
