"""
Moddule pour définir les types et les protocoles des modèles des stations.

Ce module contient les types et les protocoles nécessaires pour définir les modèles des stations.
"""

from datetime import timedelta
from typing import Protocol, Optional


class EndpointTypeProtocol(Protocol):
    """
    Protocole pour définir les types des endpoints.
    """

    PUBLIC: str = "EndpointPublic"
    """Endpoint public."""
    PRIVATE_PROD: str = "EndpointPrivateProd"
    """Endpoint privé de production."""
    PRIVATE_DEV: str = "EndpointPrivateDev"
    """Endpoint privé de développement."""


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


class ResponseProtocol(Protocol):
    """
    Protocole pour définir les types des réponses des API.
    """

    status_code: int
    """Code de statut de la réponse."""
    is_ok: bool
    """Indique si la réponse est valide."""
    message: str
    """Message de la réponse."""
    error: str
    """Erreur de la réponse."""
    data: list[dict]
    """Données de la réponse."""


class IWLSapiProtocol(Protocol):
    """
    Protocole pour définir les méthode des différent types API.
    """

    def get_all_stations(self, **kwargs) -> ResponseProtocol:
        """
        Méthode pour récupérer toutes les stations.

        :return: Réponse de la requête.
        :rtype: ResponseProtocol
        """
        pass

    def get_time_series_station(self, station: str) -> ResponseProtocol:
        """
        Méthode pour récupérer les séries temporelles d'une station.

        :param station: Code de la station.
        :type station: str
        :return: Réponse de la requête.
        :rtype: ResponseProtocol
        """
        pass

    def get_metadata_station(self, station: str) -> ResponseProtocol:
        """
        Méthode pour récupérer les métadonnées d'une station.

        :param station: Code de la station.
        :type station: str
        :return: Réponse de la requête.
        :rtype: ResponseProtocol
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

        :param station: Code de la station.
        :type station: str
        :param from_time: Date de début.
        :type from_time: str
        :param to_time: Date de fin.
        :type to_time: str
        :param time_serie_code: Code de la série temporelle.
        :type time_serie_code: Optional[TimeSeriesProtocol]
        :param time_delta: Intervalle de temps.
        :type time_delta: timedelta
        :param datetime_sorted: Indique si les données sont triées par date.
        :type datetime_sorted: bool
        :return: Réponse de la requête.
        :rtype: ResponseProtocol
        """
        pass
