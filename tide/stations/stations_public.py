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

    def get_stations_geodataframe(
        self,
        filter_time_series: Collection[TimeSeriesProtocol] | None,
        station_name_key: Optional[str] = "officialName",
        **kwargs,
    ) -> gpd.GeoDataFrame:
        """
        Récupère les données des stations sous forme de GeoDataFrame.

        :param filter_time_series: (Collection[TimeSeriesProtocol] | None) Liste des séries temporelles pour filtrer
                                        les stations. Si None, toutes les stations sont retournées.
        :param station_name_key: (str) Clé du nom de la station.
        :return: (gpd.DataFrame) Données des stations sous forme de GeoDataFrame.
        """
        return self._get_stations_geodataframe(
            stations=self.stations,
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
