from datetime import datetime
from typing import Optional, Collection

from dateutil import parser
import geopandas as gpd
from loguru import logger

from .stations_abc import StationsHandlerABC
from .stations_models import TimeSeriesProtocol, IWLSapiProtocol

LOGGER = logger.bind(name="CSB-Pipeline.Tide.Station.Public")


class StationsHandlerPublic(StationsHandlerABC):
    def __init__(self, api: IWLSapiProtocol):
        super().__init__(api=api)

    @staticmethod
    def _filter_stations(
        stations: Collection[dict], filter_time_series: Collection[TimeSeriesProtocol]
    ) -> list[dict]:
        """
        Filtre les stations en fonction des séries temporelles.

        :param stations: (Collection[dict]) Liste des stations.
        :param filter_time_series: (Collection[TimeSeriesProtocol]) Liste des séries temporelles pour filtrer les stations.
        :return: (list[dict]) Liste des stations filtrées.
        """
        LOGGER.debug(
            f"Filtrage des stations en fonction des séries temporelles : {filter_time_series}."
        )

        return [
            station
            for station in stations
            if any(ts["code"] in filter_time_series for ts in station["timeSeries"])
        ]

    @staticmethod
    def _get_time_series(
        station: dict, index_map: dict[TimeSeriesProtocol, int] | None
    ) -> list[str]:
        """
        Récupère les séries temporelles de la station.

        :param station: (dict) Données de la station.
        :param index_map: (dict[str, int] | None) Carte d'index pour les séries temporelles.
        :return: (list[str]) Liste des séries temporelles.
        """
        return [
            ts["code"] for ts in station["timeSeries"] if ts["code"] in index_map.keys()
        ]

    def _get_stations_with_metadata(
        self, ttl: int, api: str = "public", column_name_tidal: str = "isTidal"
    ) -> list[dict]:
        """
        Récupère les données des stations avec les séries temporelles.

        :param ttl: (int) Durée de vie du cache en secondes.
        :param api: (str) Nom de l'API.
        :param column_name_tidal: (str) Nom de la colonne pour les informations sur les marées.
        :return: (list[dict]) Données des stations avec les séries temporelles.
        """
        LOGGER.debug("Récupération des métadonnées des stations.")

        stations: list[dict] = [station["id"] for station in self.stations]

        tidal_info_list: list[bool | None] = self._get_stations_tidal_info(
            stations=stations, ttl=ttl, api=api, column_name=column_name_tidal
        )

        for station, is_tidal in zip(stations, tidal_info_list):
            station["isTidal"] = is_tidal

        return stations

    def get_stations_geodataframe(
        self,
        filter_time_series: Collection[TimeSeriesProtocol] | None,
        station_name_key: Optional[str] = "officialName",
        ttl: Optional[int] = 86400,
    ) -> gpd.GeoDataFrame:
        """
        Récupère les données des stations sous forme de GeoDataFrame.

        :param filter_time_series: (Collection[TimeSeriesProtocol] | None) Liste des séries temporelles pour filtrer
                                        les stations. Si None, toutes les stations sont retournées.
        :param station_name_key: (str) Clé du nom de la station.
        :param ttl: (int) Durée de vie du cache en secondes.
        :return: (gpd.DataFrame) Données des stations sous forme de GeoDataFrame.
        """
        return self._get_stations_geodataframe(
            stations=self._get_stations_with_metadata(ttl=ttl),
            filter_time_series=filter_time_series,
            station_name_key=station_name_key,
        )

    @staticmethod
    def _get_event_date(event: dict) -> datetime:
        """
        Récupère la date de l'événement.

        :param event: (dict) Données de l'événement.
        :return: (datetime) Date de l'événement.
        """
        return parser.isoparse(event["eventDate"])

    @staticmethod
    def _get_qc_flag(event: dict) -> str:
        """
        Récupère le type du flag de qualité.

        :param event: (dict) Données de l'événement.
        :return: (str) Type du flag de qualité.
        """
        return event["qcFlagCode"]
