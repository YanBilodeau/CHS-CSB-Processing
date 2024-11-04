from abc import ABC, abstractmethod
from datetime import timedelta, datetime
from typing import Optional, Collection

import geopandas as gpd
import pandas as pd
from loguru import logger
from shapely.geometry import Point

from .exception_stations import StationsError
from .stations_models import TimeSeriesProtocol, ResponseProtocol, IWLSapiProtocol
from ..schema import StationsSchema, validate_schema, TimeSerieDataSchema

LOGGER = logger.bind(name="CSB-Pipeline.Tide.Station.ABC")


class StationsHandlerABC(ABC):
    def __init__(self, api: IWLSapiProtocol):
        LOGGER.debug(f"Initialisation d'un objet {self.__class__.__name__}.")

        self.api: IWLSapiProtocol = api

    @property
    def stations(self) -> list[dict]:
        stations: ResponseProtocol = self.api.get_all_stations()  # type: ignore

        if not stations.is_ok:
            LOGGER.error(
                f"Erreur lors de la récupération des stations: {stations.message} - {stations.error}."
            )
            raise StationsError(
                message=stations.message,
                error=stations.error,
                status_code=stations.status_code,
            )

        return stations.data

    @staticmethod
    def _create_index_map(
        filter_time_series: Collection[TimeSeriesProtocol],
    ) -> dict[TimeSeriesProtocol, int]:
        """
        Crée une carte d'index pour les séries temporelles.

        :param filter_time_series: (Collection[TimeSeriesProtocol]) Liste des séries temporelles en ordre de priorité.
        :return: (dict[TimeSeriesProtocol, int]) Carte d'index pour les séries temporelles.
        """
        return {code: index for index, code in enumerate(filter_time_series)}

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
    def _create_geometry(stations: Collection[dict]) -> list[Point]:
        """
        Crée une liste de points à partir des données des stations.

        :param stations: (Collection[dict]) Liste des stations.
        :return: (list[Point]) Liste des points.
        """
        LOGGER.debug("Création des géométries des stations.")

        return [
            Point(station["longitude"], station["latitude"]) for station in stations
        ]

    @staticmethod
    def _create_attributes(
        stations: Collection[dict],
        index_map: dict[TimeSeriesProtocol, int] | None,
        station_name_key: str,
    ) -> list[dict]:
        """
        Crée une liste d'attributs pour les stations.

        :param stations: (Collection[dict]) Liste des stations.
        :param index_map: (dict[str, int] | None) Carte d'index pour les séries temporelles.
        :param station_name_key: (str) Clé du nom de la station.
        :return: (list[dict]) Liste des attributs.
        """
        LOGGER.debug("Création des attributs des stations.")

        return [
            {
                "id": station["id"],
                "code": station["code"],
                "name": station[station_name_key],
                "time_series": (
                    ["Unknown"]
                    if index_map is None
                    else sorted(
                        [
                            ts["code"]
                            for ts in station["timeSeries"]
                            if ts["code"] in index_map.keys()
                        ],
                        key=lambda code: index_map.get(code, float("inf")),
                    )
                ),
            }
            for station in stations
        ]

    def _get_stations_geodataframe(
        self,
        stations: Collection[dict],
        filter_time_series: Collection[TimeSeriesProtocol] | None,
        station_name_key: str,
    ) -> gpd.GeoDataFrame:
        """
        Récupère les données des stations sous forme de GeoDataFrame.

        :param stations: (Collection[dict]) Liste des stations.
        :param filter_time_series: (Collection[TimeSeriesProtocol] | None) Liste des séries temporelles pour filtrer
                                        les stations. Si None, toutes les stations sont retournées.
        :param station_name_key: (str) Clé du nom de la station.
        :return: (gpd.DataFrame) Données des stations sous forme de GeoDataFrame.
        """
        LOGGER.debug("Création du GeoDataFrame des stations.")

        filtered_stations: list[dict] = (
            self._filter_stations(
                stations=stations, filter_time_series=filter_time_series
            )
            if filter_time_series
            else stations
        )

        geometry: list[Point] = self._create_geometry(stations=filtered_stations)
        attributes: list[dict] = self._create_attributes(
            stations=filtered_stations,
            index_map=(
                self._create_index_map(filter_time_series)
                if filter_time_series
                else None
            ),
            station_name_key=station_name_key,
        )

        gdf_stations: gpd.GeoDataFrame[StationsSchema] = gpd.GeoDataFrame(
            attributes, geometry=geometry, crs="EPSG:4326"
        )
        validate_schema(df=gdf_stations, schema=StationsSchema)

        return gdf_stations

    @abstractmethod
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
        ...

    @staticmethod
    @abstractmethod
    def _get_event_date(event: dict) -> datetime:
        """
        Récupère la date de l'événement.

        :param event: (dict) Données de l'événement.
        :return: (datetime) Date de l'événement.
        """
        ...

    def create_data_list(
        self, data: Collection[dict], time_serie_code: TimeSeriesProtocol
    ) -> list[dict]:
        """
        Crée une liste de données pour les séries temporelles.

        :param data: (Collection[dict]) Données de la série temporelle.
        :param time_serie_code: (TimeSeriesProtocol) Le code de la série temporelle.
        :return: (list[dict]) Liste des données.
        """
        return [
            {
                "event_date": self._get_event_date(event=event),
                "value": event["value"],
                "time_serie_code": time_serie_code,
            }
            for event in data
        ]

    def get_time_series_dataframe(
        self,
        station: str,
        from_time: str,
        to_time: str,
        time_serie_code: Optional[TimeSeriesProtocol],
        time_delta: timedelta = timedelta(days=7),
        datetime_sorted: bool = True,
        **kwargs,
    ) -> pd.DataFrame:
        """
        Récupère les séries temporelles sous forme de DataFrame.

        :param station: (str) Code de la station.
        :param from_time: (str) La date de début en format ISO 8601 (ex: 2019-11-13T19:18:00Z).
        :param to_time: (str) La date de fin en format ISO 8601 (ex: 2019-11-13T19:18:00Z).
        :param time_serie_code: (TimeSeriesProtocol) Le code de la série temporelle désirée.
        :param time_delta: (timedelta) L'intervalle de temps maximale pour chaque requête.
        :param datetime_sorted: (bool) Si les données doivent être triées par date.
        :return: (pd.DataFrame) Données des séries temporelles sous forme de DataFrame.
        """
        LOGGER.debug(
            f"Récupération des données {time_serie_code} pour la station '{station}' du {from_time} au {to_time} "
            f"par block de {time_delta}."
        )

        data: ResponseProtocol = self.api.get_time_serie_block_data(
            station=station,
            from_time=from_time,
            to_time=to_time,
            time_serie_code=time_serie_code,
            time_delta=time_delta,
            datetime_sorted=datetime_sorted,
            **kwargs,
        )

        if not data.is_ok:
            LOGGER.error(
                f"Status code {data.status_code} : Erreur lors de la récupération des données pour la station "
                f"'{station}' et la série temporelle '{time_serie_code}' entre le {from_time} et le {to_time}. "
                f"{data.message} - {data.error}."
            )
            return pd.DataFrame()

        if not data.data:
            LOGGER.warning(
                f"Aucune donnée pour la station '{station}' et la série temporelle '{time_serie_code}' "
                f"entre le {from_time} et le {to_time}."
            )
            return pd.DataFrame()

        data_list: list[dict] = self.create_data_list(
            data=data.data, time_serie_code=time_serie_code  # type: ignore
        )

        data_dataframe: pd.DataFrame[TimeSerieDataSchema] = pd.DataFrame(data_list)
        validate_schema(df=data_dataframe, schema=TimeSerieDataSchema)

        return data_dataframe
