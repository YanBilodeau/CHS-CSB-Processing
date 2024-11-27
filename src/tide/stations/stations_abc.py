"""
Module ABC récupérer des données des stations de marée.

Ce module contient la classe abstraite `StationsHandlerABC` qui définit les méthodes pour récupérer les données stations de marée.
"""

from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta, datetime
from itertools import repeat
from typing import Optional, Collection

import geopandas as gpd
import pandas as pd
from loguru import logger
from shapely.geometry import Point

from .cache_wrapper import cache_result
from .exception_stations import StationsError
from .stations_models import TimeSeriesProtocol, ResponseProtocol, IWLSapiProtocol
from ..schema import StationsSchema, validate_schema, TimeSerieDataSchema

LOGGER = logger.bind(name="CSB-Pipeline.Tide.Station.ABC")


class StationsHandlerABC(ABC):
    """
    Classe abstraite pour récupérer des données stations de marée.
    """
    def __init__(self, api: IWLSapiProtocol):
        """
        Initialisation de la classe abstraite `StationsHandlerABC`.

        :param api: (IWLSapiProtocol) API pour récupérer les données des stations.
        """
        LOGGER.debug(f"Initialisation d'un objet {self.__class__.__name__}.")

        self.api: IWLSapiProtocol = api

    @property
    def stations(self) -> list[dict]:
        """
        Récupère la liste des stations.

        :return: (list[dict]) Liste des stations.
        """
        stations: ResponseProtocol = self.api.get_all_stations()

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
    @abstractmethod
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
        ...

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
    @abstractmethod
    def _get_time_series(
        station: dict, index_map: dict[TimeSeriesProtocol, int] | None
    ) -> list[str]:
        """
        Récupère les séries temporelles de la station.

        :param station: (dict) Données de la station.
        :param index_map: (dict[str, int] | None) Carte d'index pour les séries temporelles.
        :return: (list[str]) Liste des séries temporelles.
        """
        ...

    def _create_attributes(
        self,
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
                "name": station[station_name_key].replace("/", "-"),
                "time_series": (
                    ["Unknown"]
                    if index_map is None
                    else sorted(
                        self._get_time_series(station=station, index_map=index_map),
                        key=lambda code: index_map.get(code, float("inf")),
                    )
                ),
                "is_tidal": str(station["isTidal"]),
            }
            for station in stations
        ]

    def _fetch_is_tidal_station(
        self, sation_id: str, ttl: int, api: str, column_name: str
    ) -> bool | None:
        """
        Récupère l'information si la station est une station de marée.

        :param sation_id: (str) Identifiant de la station.
        :param ttl: (int) Durée de vie du cache en secondes.
        :param api: (str) Type de l'API.
        :param column_name: (str) Nom de la colonne.
        :return: (bool | None) True si la station est une station de marée, False sinon.
        """

        @cache_result(ttl=ttl)
        def _is_tidal_station(station_id_: str, **kwargs) -> bool | None:
            metadata: dict = self.api.get_metadata_station(  # type: ignore[arg-type]
                station=station_id_
            ).data

            if metadata is None:
                return None

            return metadata.get(column_name)

        return _is_tidal_station(station_id_=sation_id, api=api)

    def _get_stations_tidal_info(
        self, stations: list[dict], ttl: int, api: str, column_name: str
    ) -> list[bool | None]:
        """
        Récupère les informations sur les stations de marée.

        :param stations: (list[dict]) Liste des stations.
        :param ttl: (int) Durée de vie du cache en secondes.
        :param api: (str) Type de l'API.
        :param column_name: (str) Nom de la colonne.
        :return: (list[bool | None]) Liste des informations sur les stations de marée.
        """
        with ThreadPoolExecutor(max_workers=10) as executor:
            tidal_info_list = list(
                executor.map(
                    self._fetch_is_tidal_station,
                    stations,
                    repeat(ttl),
                    repeat(api),
                    repeat(column_name),
                )
            )

        return tidal_info_list

    def _get_stations_geodataframe(
        self,
        stations: Collection[dict],
        filter_time_series: Collection[TimeSeriesProtocol] | None,
        excluded_stations: Collection[str] | None,
        station_name_key: str,
    ) -> gpd.GeoDataFrame:
        """
        Récupère les données des stations sous forme de GeoDataFrame.

        :param stations: (Collection[dict]) Liste des stations.
        :param filter_time_series: (Collection[TimeSeriesProtocol] | None) Liste des séries temporelles pour filtrer
                                        les stations. Si None, toutes les stations sont retournées.
        :param excluded_stations: (Collection[str] | None) Liste des stations à exclure.
        :param station_name_key: (str) Clé du nom de la station.
        :return: (gpd.DataFrame) Données des stations sous forme de GeoDataFrame.
        """
        LOGGER.debug("Création du GeoDataFrame des stations.")

        filtered_stations: list[dict] = (
            self._filter_stations(
                stations=stations,
                filter_time_series=filter_time_series,
                excluded_stations=excluded_stations,
            )
            if filter_time_series or excluded_stations
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
        excluded_stations: Collection[str] | None = None,
        station_name_key: Optional[str] = "officialName",
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

    @staticmethod
    @abstractmethod
    def _get_qc_flag(event: dict) -> str:
        """
        Récupère le type du flag de qualité.

        :param event: (dict) Données de l'événement.
        :return: (str) Type du flag de qualité.
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
                "qc_flag": self._get_qc_flag(event=event),
            }
            for event in data
        ]

    @staticmethod
    def filter_wlo_qc_flag(
        data_dataframe: pd.DataFrame,
        time_serie_code: TimeSeriesProtocol,
        wlo_qc_flag_filter: Optional[Collection[str] | None] = None,
    ) -> pd.DataFrame:
        """
        Filtre les données de la série temporelle WLO en fonction des flags de qualité.

        :param data_dataframe: (pd.DataFrame) Données des séries temporelles sous forme de DataFrame.
        :param time_serie_code: (TimeSeriesProtocol) Le code de la série temporelle des données.
        :param wlo_qc_flag_filter: (Collection[str] | None) Liste des flags de qualité à filtrer pour la
                                        série temporelle WLO.
        :return: (pd.DataFrame) Données des séries temporelles sous forme de DataFrame.
        """
        if time_serie_code == TimeSeriesProtocol.WLO:
            data_dataframe = (
                data_dataframe[~data_dataframe["qc_flag"].isin(wlo_qc_flag_filter)]
                if wlo_qc_flag_filter
                else data_dataframe
            )

        return data_dataframe

    def get_time_series_dataframe(
        self,
        station: str,
        from_time: str,
        to_time: str,
        time_serie_code: Optional[TimeSeriesProtocol],
        time_delta: Optional[timedelta] = timedelta(days=7),
        datetime_sorted: Optional[bool] = True,
        wlo_qc_flag_filter: Optional[Collection[str] | None] = None,
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
        :param wlo_qc_flag_filter: (Collection[str] | None) Liste des flags de qualité à filtrer pour la série temporelle WLO.
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

        data_dataframe = self.filter_wlo_qc_flag(
            data_dataframe=data_dataframe,
            time_serie_code=time_serie_code,
            wlo_qc_flag_filter=wlo_qc_flag_filter,
        )

        data_dataframe.drop(columns=["qc_flag"], inplace=True)

        validate_schema(df=data_dataframe, schema=TimeSerieDataSchema)

        return data_dataframe
