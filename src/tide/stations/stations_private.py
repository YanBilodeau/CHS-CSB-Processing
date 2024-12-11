"""
Module pour récupérer des données des stations de l'API privé.

Ce module contient la classe StationsHandlerPrivate qui permet de récupérer les données des stations de l'API privé.
"""

from concurrent.futures import ThreadPoolExecutor
import copy
from datetime import datetime, UTC
from itertools import repeat
from pathlib import Path
from typing import Optional, Collection

import geopandas as gpd
from loguru import logger

from .cache_wrapper import cache_result
from .stations_abc import StationsHandlerABC
from .stations_models import TimeSeriesProtocol, IWLSapiProtocol

LOGGER = logger.bind(name="CSB-Pipeline.Tide.Station.Private")


class StationsHandlerPrivate(StationsHandlerABC):
    """
    Classe récupérer des données stations de l'API privé.
    """

    def __init__(
        self,
        api: IWLSapiProtocol,
        ttl: int = 86400,
        cache_path: Optional[Path] = Path(__file__).parent / "cache",
    ):
        """
        Constructeur de la classe StationsHandlerPrivate.

        :param api: Instance de l'API.
        :type api: IWLSapiProtocol
        :param ttl: Durée de vie du cache en secondes.
        :type ttl: int
        :param cache_path: Chemin du cache.
        :type cache_path: Optional[Path]
        """
        super().__init__(api=api, ttl=ttl, cache_path=cache_path)

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

        :param station: Données de la station.
        :type station: dict
        :param index_map: Carte d'index pour les séries temporelles.
        :type index_map: dict[TimeSeriesProtocol, int] | None
        :return: Liste des séries temporelles.
        :rtype: list[str]
        """
        return [
            ts["code"]
            for ts in station["timeSeries"]
            if ts["code"] in index_map.keys() and ts["active"]
        ]

    def _fetch_time_series(self, station_id: str, api: str) -> dict:
        """
        Récupère les séries temporelles de la station.

        :param station_id: Identifiant de la station.
        :type station_id: str
        :param api: Type d'API.
        :type api: str
        :return: Données de la station avec les séries temporelles.
        :rtype: dict
        """

        @cache_result(ttl=self.ttl)
        def _get_time_series_station(station_id_: str, **kwargs) -> list[dict]:
            return self.api.get_time_series_station(station=station_id_).data

        return _get_time_series_station(station_id_=station_id, api=api)  # type: ignore[arg-type]

    def _get_stations_time_series(self, stations: list[dict], api: str) -> list[dict]:
        """
        Récupère les séries temporelles des stations.

        :param stations: Liste des stations.
        :type stations: list[dict]
        :param api: ype d'API.
        :type api: str
        :return: Liste des stations avec les séries temporelles.
        :rtype: list[dict]
        """
        with ThreadPoolExecutor(max_workers=10) as executor:
            time_series_list = list(
                executor.map(
                    self._fetch_time_series,
                    stations,
                    repeat(api),
                )
            )

        return time_series_list

    def _get_stations_with_metadata(
        self, api: str = "private", column_name_tidal: str = "tidal"
    ) -> list[dict]:
        """
        Récupère les données des stations avec les séries temporelles.

        :param api: Nom de l'API.
        :type api: str
        :param column_name_tidal: Nom de la colonne pour les informations de marée.
        :type column_name_tidal: str
        :return: Données des stations avec les séries temporelles.
        :rtype: list[dict]
        """
        LOGGER.debug(
            "Récupération des métadonnées et des séries temporelles des stations."
        )

        stations: list[dict] = copy.deepcopy(self.stations)
        stations_id: list[dict] = [station["id"] for station in stations]

        time_series_list: list[dict] = self._get_stations_time_series(
            stations=stations_id, api=api
        )

        tidal_info_list: list[bool | None] = self._get_stations_tidal_info(
            stations=stations_id, api=api, column_name=column_name_tidal
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
    ) -> gpd.GeoDataFrame:
        """
        Récupère les données des stations sous forme de GeoDataFrame.

        :param filter_time_series: Liste des séries temporelles pour filtrer les stations. Si None, toutes les stations sont retournées.
        :type filter_time_series: Collection[TimeSeriesProtocol] | None
        :param excluded_stations: Liste des stations à exclure.
        :type excluded_stations: Collection[str] | None
        :param station_name_key: Clé du nom de la station.
        :type station_name_key: str
        :return: Données des stations sous forme de GeoDataFrame.
        :rtype: gpd.GeoDataFrame
        """
        return self._get_stations_geodataframe(
            stations=self._get_stations_with_metadata(),
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
        return datetime.fromtimestamp(event["eventDateEpoch"] / 1000, tz=UTC)

    @staticmethod
    def _get_qc_flag(event: dict) -> str:
        """
        Récupère le type du flag de qualité.

        :param event: Données de l'événement.
        :type event: dict
        :return: Type du flag de qualité.
        :rtype: str
        """
        return event["qcFlag"]
