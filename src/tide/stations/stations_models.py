"""
Moddule pour définir les types et les protocoles des modèles des stations.

Ce module contient les types et les protocoles nécessaires pour définir les modèles des stations.
"""

from datetime import timedelta
from typing import Protocol, Optional


class EndpointTypeProtocol(Protocol):
    """
    Protocole pour définir les types des endpoints.

    PUBLIC: Endpoint public.
    PRIVATE_PROD: Endpoint privé de production.
    PRIVATE_DEV: Endpoint privé de développement
    """

    PUBLIC: str = "EndpointPublic"
    PRIVATE_PROD: str = "EndpointPrivateProd"
    PRIVATE_DEV: str = "EndpointPrivateDev"


class TimeSeriesProtocol(Protocol):
    """
    Protocole pour définir les types des séries temporelles.

    WLO: Water Level Observed.
    WLF_SPINE: Water Level Forecast Spine.
    WLF_VTG: Water Level Forecast VTG.
    WLF: Water Level Forecast.
    WLP: Water Level Prediction.
    """

    WLO: str = "wlo"
    WLF_SPINE: str = "wlf-spine"
    WLF_VTG: str = "wlf-vtg"
    WLF: str = "wlf"
    WLP: str = "wlp"

    def from_str(cls, value: str):
        pass


class ResponseProtocol(Protocol):
    """
    Protocole pour définir les types des réponses des API.

    status_code: (int) Code de statut de la réponse.
    is_ok: (bool) Indique si la réponse est valide.
    message: (str) Message de la réponse.
    error: (str) Erreur de la réponse.
    data: (list[dict]) Données de la réponse.
    """

    status_code: int
    is_ok: bool
    message: str
    error: str
    data: list[dict]


class IWLSapiProtocol(Protocol):
    """
    Protocole pour définir les méthode des différent types API.
    """

    def get_all_stations(self, **kwargs) -> ResponseProtocol:
        """
        Méthode pour récupérer toutes les stations.

        :return: (ResponseProtocol) Réponse de la requête.
        """
        pass

    def get_time_series_station(self, station: str) -> ResponseProtocol:
        """
        Méthode pour récupérer les séries temporelles d'une station.

        :param station: (str) Code de la station.
        :return: (ResponseProtocol) Réponse de la requête.
        """
        pass

    def get_metadata_station(self, station: str) -> ResponseProtocol:
        """
        Méthode pour récupérer les métadonnées d'une station.

        :param station: (str) Code de la station.
        :return: (ResponseProtocol) Réponse de la requête.
        """
        pass

    def get_time_serie_block_data(
        self,
        station: str,
        from_time: str,
        to_time: str,
        time_serie_code: Optional[TimeSeriesProtocol],
        time_delta: timedelta = timedelta(days=7),
        datetime_sorted: bool = True,
        **kwargs,
    ) -> ResponseProtocol:
        """
        Méthode pour récupérer les données d'une série temporelle.

        :param station: (str) Code de la station.
        :param from_time: (str) Date de début.
        :param to_time: (str) Date de fin.
        :param time_serie_code: (TimeSeriesProtocol) Code de la série temporelle.
        :param time_delta: (timedelta) Intervalle de temps.
        :param datetime_sorted: (bool) Indique si les données sont triées par date.
        :return: (ResponseProtocol) Réponse de la requête.
        """
        pass
