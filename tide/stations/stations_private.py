from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional, Collection

from diskcache import Cache
import geopandas as gpd
from loguru import logger

from .stations_abc import StationsHandlerABC
from .stations_models import TimeSeriesProtocol, IWLSapiProtocol

LOGGER = logger.bind(name="CSB-Pipeline.Tide.Station.Private")
CACHE: Cache = Cache(str(Path(__file__).parent / "cache"))


class StationsHandlerPrivate(StationsHandlerABC):
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
            if any(
                ts["code"] in filter_time_series and ts["active"]
                for ts in station["timeSeries"]
            )
        ]

    def _fetch_time_series(self, station: dict) -> dict:
        station["timeSeries"] = self.api.get_time_series_station(
            station=station["id"]
        ).data

        return station

    def _get_stations_with_time_series(self) -> list[dict]:
        """
        Récupère les données des stations avec les séries temporelles.

        :return: (list[dict]) Données des stations avec les séries temporelles.
        """
        LOGGER.debug("Récupération des séries temporelles des stations.")

        stations: list[dict] = self.stations
        with ThreadPoolExecutor(max_workers=10) as executor:
            stations = list(executor.map(self._fetch_time_series, stations))

        return stations

    def get_stations_geodataframe(
        self,
        filter_time_series: Collection[TimeSeriesProtocol] | None,
        station_name_key: str = "name",
        use_cache: Optional[bool] = True,
        ttl: Optional[int] = 86400,
    ) -> gpd.GeoDataFrame:
        """
        Récupère les données des stations sous forme de GeoDataFrame.

        :param filter_time_series: (Collection[TimeSeriesProtocol] | None) Liste des séries temporelles pour filtrer
                                        les stations. Si None, toutes les stations sont retournées.
        :param station_name_key: (str) Clé du nom de la station.
        :param use_cache: (bool) Utilisation du cache.
        :param ttl: (int) Durée de vie du cache en secondes.
        :return: (gpd.DataFrame) Données des stations sous forme de GeoDataFrame.
        """
        cache_key: str = f"stations_{filter_time_series}"

        if use_cache and cache_key in CACHE:
            LOGGER.debug(
                f"Récupération des données des stations depuis le cache : '{cache_key}'."
            )
            return CACHE[cache_key]

        gdf_stations: gpd.GeoDataFrame = self._get_stations_geodataframe(
            stations=(
                self._get_stations_with_time_series()
                if filter_time_series
                else self.stations
            ),
            filter_time_series=filter_time_series,
            station_name_key=station_name_key,
        )

        LOGGER.debug(
            f"Sauvegarde des données des stations dans la cache avec un tll de {ttl} secondes."
        )
        CACHE.set(key=cache_key, value=gdf_stations, expire=ttl)

        return gdf_stations

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
