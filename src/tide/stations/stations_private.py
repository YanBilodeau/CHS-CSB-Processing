from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, UTC
from itertools import repeat
from typing import Optional, Collection

import geopandas as gpd
from loguru import logger

from .cache_wrapper import cache_result
from .stations_abc import StationsHandlerABC
from .stations_models import TimeSeriesProtocol, IWLSapiProtocol

LOGGER = logger.bind(name="CSB-Pipeline.Tide.Station.Private")


class StationsHandlerPrivate(StationsHandlerABC):
    def __init__(self, api: IWLSapiProtocol):
        super().__init__(api=api)

    @staticmethod
    def _filter_stations(
        stations: Collection[dict],
        filter_time_series: Collection[TimeSeriesProtocol] | None,
        excluded_stations: Collection[str] | None,
    ) -> list[dict]:
        """
        Filtre les stations en fonction des séries temporelles.

        :param stations: (Collection[dict]) Liste des stations.
        :param filter_time_series: (Collection[TimeSeriesProtocol] | None) Liste des séries temporelles pour filtrer les stations.
        :param excluded_stations: (Collection[str] | None) Liste des stations à exclure.
        :return: (list[dict]) Liste des stations filtrées.
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
                or any(
                    ts["code"] in filter_time_series and ts["active"]
                    for ts in station["timeSeries"]
                )
            )
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
            ts["code"]
            for ts in station["timeSeries"]
            if ts["code"] in index_map.keys() and ts["active"]
        ]

    def _fetch_time_series(self, station_id: str, ttl: int, api: str) -> dict:
        """
        Récupère les séries temporelles de la station.

        :param station_id: (str) Identifiant de la station.
        :param ttl: (int) Durée de vie du cache en secondes.
        :param api: (str) Type d'API.
        :return: (dict) Données de la station avec les séries temporelles.
        """

        @cache_result(ttl=ttl)
        def _get_time_series_station(station_id_: str, **kwargs) -> list[dict]:
            return self.api.get_time_series_station(station=station_id_).data

        return _get_time_series_station(station_id_=station_id, api=api)  # type: ignore[arg-type]

    def _get_stations_time_series(
        self, stations: list[dict], ttl: int, api: str
    ) -> list[dict]:
        """
        Récupère les séries temporelles des stations.

        :param stations: (list[dict]) Liste des stations.
        :param ttl: (int) Durée de vie du cache en secondes.
        :param api: (str) Type d'API.
        :return: (list[dict]) Liste des stations avec les séries temporelles.
        """
        with ThreadPoolExecutor(max_workers=10) as executor:
            time_series_list = list(
                executor.map(
                    self._fetch_time_series,
                    stations,
                    repeat(ttl),
                    repeat(api),
                )
            )

        return time_series_list

    def _get_stations_with_metadata(
        self, ttl: int, api: str = "private", column_name_tidal: str = "tidal"
    ) -> list[dict]:
        """
        Récupère les données des stations avec les séries temporelles.

        :param ttl: (int) Durée de vie du cache en secondes.
        :param api: (str) Nom de l'API.
        :param column_name_tidal: (str) Nom de la colonne pour les informations de marée.
        :return: (list[dict]) Données des stations avec les séries temporelles.
        """
        LOGGER.debug(
            "Récupération des métadonnées et des séries temporelles des stations."
        )

        stations: list[dict] = self.stations
        stations_id: list[dict] = [station["id"] for station in self.stations]

        time_series_list: list[dict] = self._get_stations_time_series(
            stations=stations_id, ttl=ttl, api=api
        )

        tidal_info_list: list[bool | None] = self._get_stations_tidal_info(
            stations=stations_id, ttl=ttl, api=api, column_name=column_name_tidal
        )

        for station, ts, is_tidal in zip(stations, time_series_list, tidal_info_list):
            station["timeSeries"] = ts
            station["isTidal"] = is_tidal

        return stations

    def get_stations_geodataframe(
        self,
        filter_time_series: Collection[TimeSeriesProtocol] | None,
        excluded_stations: Collection[str] | None = None,
        station_name_key: str = "name",
        ttl: Optional[int] = 86400,
    ) -> gpd.GeoDataFrame:
        """
        Récupère les données des stations sous forme de GeoDataFrame.

        :param filter_time_series: (Collection[TimeSeriesProtocol] | None) Liste des séries temporelles pour filtrer
                                        les stations. Si None, toutes les stations sont retournées.
        :param excluded_stations: (Collection[str] | None) Liste des stations à exclure.
        :param station_name_key: (str) Clé du nom de la station.
        :param ttl: (int) Durée de vie du cache en secondes.
        :return: (gpd.DataFrame) Données des stations sous forme de GeoDataFrame.
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

        :param event: (dict) Données de l'événement.
        :return: (datetime) Date de l'événement.
        """
        return datetime.fromtimestamp(event["eventDateEpoch"] / 1000, tz=UTC)

    @staticmethod
    def _get_qc_flag(event: dict) -> str:
        """
        Récupère le type du flag de qualité.

        :param event: (dict) Données de l'événement.
        :return: (str) Type du flag de qualité.
        """
        return event["qcFlag"]
