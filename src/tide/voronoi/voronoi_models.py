"""
Module qui contient les modèles pour manipuler les données des séries temporelles et des stations.
"""

from typing import Protocol, Collection, Optional

import geopandas as gpd


class TimeSeriesProtocol(Protocol):
    """
    Protocole pour définir les types des séries temporelles.

    :param WLO: Water Level Observed.
    :param WLF_SPINE: Water Level Forecast Spine.
    :param WLF_VTG: Water Level Forecast VTG.
    :param WLF: Water Level Forecast.
    :param WLP: Water Level Prediction.
    """

    WLO: str = "wlo"
    WLF_SPINE: str = "wlf-spine"
    WLF_VTG: str = "wlf-vtg"
    WLF: str = "wlf"
    WLP: str = "wlp"

    def from_str(cls, value: str):
        """
        Méthode pour convertir une chaîne de caractères en série temporelle.
        """
        pass


class StationsHandlerProtocol(Protocol):
    """
    Protocole pour définir les méthodes de manipulation des stations.
    """

    def get_stations_geodataframe(
        self,
        filter_time_series: Collection[TimeSeriesProtocol] | None,
        exclude_stations: Collection[str] | None,
        ttl: Optional[int],
    ) -> gpd.GeoDataFrame:
        """
        Méthode pour récupérer le GeoDataFrame des stations.

        :param filter_time_series: (Collection[TimeSeriesProtocol] | None) Liste des séries temporelles pour filtrer
                                        les stations. Si None, toutes les stations sont retournées.
        :param exclude_stations: (Collection[str] | None) Liste des stations à exclure.
        :param ttl: (Optional[int]) Durée de vie du cache.
        """
        pass
