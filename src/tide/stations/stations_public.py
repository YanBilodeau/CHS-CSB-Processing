"""
Module pour récupérer des données des stations de l'API public.

Ce module contient la classe StationsHandlerPublic qui permet de récupérer des données des stations de l'API public.
"""

from datetime import datetime
from typing import Optional, Collection

from dateutil import parser
import geopandas as gpd
from loguru import logger

from .stations_abc import StationsHandlerABC
from .stations_models import TimeSeriesProtocol, IWLSapiProtocol

LOGGER = logger.bind(name="CSB-Pipeline.Tide.Station.Public")


class StationsHandlerPublic(StationsHandlerABC):
    """
    Classe récupérer des données des stations de l'API public.
    """

    def __init__(self, api: IWLSapiProtocol):
        """
        Constructeur de la classe StationsHandlerPublic.

        :param api: Instance de l'API.
        :type api: IWLSapiProtocol
        """
        super().__init__(api=api)

    @staticmethod
    def _filter_stations(
        stations: Collection[dict],
        filter_time_series: Collection[TimeSeriesProtocol] | None,
        excluded_stations: Collection[str] | None,
    ) -> list[dict]:
        """
        Filtre les stations en fonction des séries temporelles.

        :param stations: Liste des stations.
        :type stations: Collection[dict]
        :param filter_time_series: Liste des séries temporelles pour filtrer les stations.
        :type filter_time_series: Collection[TimeSeriesProtocol] | None
        :param excluded_stations: Liste des stations à exclure.
        :type excluded_stations: Collection[str] | None
        :return: Liste des stations filtrées.
        :rtype: list[dict]
        """
        LOGGER.debug(
            f"Filtrage des stations en fonction des séries temporelles [{filter_time_series}] "
            f"et des stations exclues [{excluded_stations}]."
        )

        return [
            station
            for station in stations
            if (not excluded_stations or station["id"] not in excluded_stations)
            and (
                not filter_time_series
                or any(ts["code"] in filter_time_series for ts in station["timeSeries"])
            )
        ]

    @staticmethod
    def _get_time_series(
        station: dict, index_map: dict[TimeSeriesProtocol, int] | None
    ) -> list[str]:
        """
        Récupère les séries temporelles de la station.

        :param station: Données de la station.
        :type station: dict
        :param index_map: Carte d'index pour les séries temporelles.
        :type index_map: dict[TimeSeriesProtocol, int] | None
        :return: Liste des séries temporelles.
        :rtype: list[str]
        """
        return [
            ts["code"] for ts in station["timeSeries"] if ts["code"] in index_map.keys()
        ]

    def _get_stations_with_metadata(
        self, ttl: int, api: str = "public", column_name_tidal: str = "isTidal"
    ) -> list[dict]:
        """
        Récupère les données des stations avec les séries temporelles.

        :param ttl: Durée de vie du cache en secondes.
        :type ttl: int
        :param api: Nom de l'API.
        :type api: str
        :param column_name_tidal: Nom de la colonne pour les informations sur les marées.
        :type column_name_tidal: str
        :return: Données des stations avec les séries temporelles.
        :rtype: list[dict]
        """
        LOGGER.debug("Récupération des métadonnées des stations.")

        stations: list[dict] = self.stations
        stations_id: list[dict] = [station["id"] for station in stations]

        tidal_info_list: list[bool | None] = self._get_stations_tidal_info(
            stations=stations_id, ttl=ttl, api=api, column_name=column_name_tidal
        )

        for station, is_tidal in zip(stations, tidal_info_list):
            station["isTidal"] = is_tidal

        return stations

    def get_stations_geodataframe(
        self,
        filter_time_series: Collection[TimeSeriesProtocol] | None,
        excluded_stations: Collection[str] | None = None,
        station_name_key: Optional[str] = "officialName",
        ttl: Optional[int] = 86400,
    ) -> gpd.GeoDataFrame:
        """
        Récupère les données des stations sous forme de GeoDataFrame.

        :param filter_time_series: Liste des séries temporelles pour filtrer les stations. Si None, toutes les stations sont retournées.
        :type filter_time_series: Collection[TimeSeriesProtocol] | None
        :param excluded_stations: Liste des stations à exclure.
        :type excluded_stations: Collection[str] | None
        :param station_name_key: Clé du nom de la station.
        :type station_name_key: Optional[str]
        :param ttl: Durée de vie du cache en secondes.
        :type ttl: Optional[int]
        :return: Données des stations sous forme de GeoDataFrame.
        :rtype: gpd.GeoDataFrame
        """
        return self._get_stations_geodataframe(
            stations=self._get_stations_with_metadata(ttl=ttl),
            filter_time_series=filter_time_series,
            excluded_stations=excluded_stations,
            station_name_key=station_name_key,
        )

    @staticmethod
    def _get_event_date(event: dict) -> datetime:
        """
        Récupère la date de l'événement.

        :param event: Données de l'événement.
        :type event: dict
        :return: Date de l'événement.
        :rtype: datetime
        """
        return parser.isoparse(event["eventDate"])

    @staticmethod
    def _get_qc_flag(event: dict) -> str:
        """
        Récupère le type du flag de qualité.

        :param event: Données de l'événement.
        :type event: dict
        :return: Type du flag de qualité.
        :rtype: str
        """
        return event["qcFlagCode"]
