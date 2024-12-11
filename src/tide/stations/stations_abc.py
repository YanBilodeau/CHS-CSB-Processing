"""
Module ABC récupérer des données des stations de marée.

Ce module contient la classe abstraite `StationsHandlerABC` qui définit les méthodes pour récupérer les données stations de marée.
"""

from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta, datetime
from itertools import repeat
from pathlib import Path
from typing import Optional, Collection

import geopandas as gpd
import pandas as pd
from loguru import logger
from shapely.geometry import Point

from .cache_wrapper import cache_result, init_cache
from .exception_stations import StationsError
from .stations_models import TimeSeriesProtocol, ResponseProtocol, IWLSapiProtocol
import schema
from schema import model_ids as schema_ids, validate_schemas

LOGGER = logger.bind(name="CSB-Pipeline.Tide.Station.ABC")


class StationsHandlerABC(ABC):
    """
    Classe abstraite pour récupérer des données stations de marée.
    """

    def __init__(
        self,
        api: IWLSapiProtocol,
        ttl: int = 86400,
        cache_path: Optional[Path] = Path(__file__).parent / "cache",
    ):
        """
        Initialisation de la classe abstraite `StationsHandlerABC`.

        :param api: API pour récupérer les données des stations.
        :type api: IWLSapiProtocol
        :param ttl: Durée de vie du cache en secondes.
        :type ttl: int
        :param cache_path: Chemin du cache.
        :type cache_path: Path
        """
        LOGGER.debug(f"Initialisation d'un objet {self.__class__.__name__}.")

        self.api: IWLSapiProtocol = api
        self.ttl: int = ttl
        init_cache(cache_path=cache_path)

    @property
    def stations(self) -> list[dict]:
        """
        Récupère la liste des stations.

        :return: Liste des stations.
        :rtype: list[dict]
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

        :param filter_time_series: Liste des séries temporelles en ordre de priorité.
        :type filter_time_series: Collection[TimeSeriesProtocol]
        :return: Carte d'index pour les séries temporelles.
        :rtype: dict[TimeSeriesProtocol, int]
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

        :param stations: Liste des stations.
        :type stations: Collection[dict]
        :param filter_time_series: Liste des séries temporelles pour filtrer les stations.
        :type filter_time_series: Collection[TimeSeriesProtocol] | None
        :param excluded_stations: Liste des stations à exclure.
        :type excluded_stations: Collection[str] | None
        :return: Liste des stations filtrées.
        :rtype: list[dict]
        """
        ...

    @staticmethod
    def _create_geometry(stations: Collection[dict]) -> list[Point]:
        """
        Crée une liste de points à partir des données des stations.

        :param stations: Liste des stations.
        :type stations: Collection[dict]
        :return: Liste des points.
        :rtype: list[Point]
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

        :param station: Données de la station.
        :type station: dict
        :param index_map: Carte d'index pour les séries temporelles.
        :type index_map: dict[str, int] | None
        :return: Liste des séries temporelles.
        :rtype: list[str]
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

        :param stations: Liste des stations.
        :type stations: Collection[dict]
        :param index_map: Carte d'index pour les séries temporelles.
        :type index_map: dict[str, int] | None
        :param station_name_key: Clé du nom de la station.
        :type station_name_key: str
        :return: Liste des attributs.
        :rtype: list[dict]
        """
        LOGGER.debug("Création des attributs des stations.")

        return [
            {
                schema_ids.ID: station["id"],
                schema_ids.CODE: station["code"],
                schema_ids.NAME: station[station_name_key].replace("/", "-"),
                schema_ids.TIME_SERIES: (
                    ["Unknown"]
                    if index_map is None
                    else sorted(
                        self._get_time_series(station=station, index_map=index_map),
                        key=lambda code: index_map.get(code, float("inf")),
                    )
                ),
                schema_ids.IS_TIDAL: str(station["isTidal"]),
            }
            for station in stations
        ]

    def _fetch_is_tidal_station(
        self, sation_id: str, api: str, column_name: str
    ) -> bool | None:
        """
        Récupère l'information si la station est une station de marée.

        :param sation_id: dentifiant de la station.
        :type sation_id: str
        :param api: Type de l'API.
        :type api: str
        :param column_name: Nom de la colonne.
        :type sation_id: str
        :return: True si la station est une station de marée, False sinon.
        :rtype: bool | None
        """

        @cache_result(ttl=self.ttl)
        def _is_tidal_station(station_id_: str, **kwargs) -> bool | None:
            metadata: dict = self.api.get_metadata_station(  # type: ignore[arg-type]
                station=station_id_
            ).data

            if metadata is None:
                return None

            return metadata.get(column_name)

        return _is_tidal_station(station_id_=sation_id, api=api)

    def _get_stations_tidal_info(
        self, stations: list[dict], api: str, column_name: str
    ) -> list[bool | None]:
        """
        Récupère les informations sur les stations de marée.

        :param stations: Liste des stations.
        :type stations: list[dict]
        :param api: Type de l'API.
        :type api: str
        :param column_name: Nom de la colonne.
        :type column_name: str
        :return: Liste des informations sur les stations de marée.
        :rtype: list[bool | None]
        """
        with ThreadPoolExecutor(max_workers=10) as executor:
            tidal_info_list = list(
                executor.map(
                    self._fetch_is_tidal_station,
                    stations,
                    repeat(api),
                    repeat(column_name),
                )
            )

        return tidal_info_list

    @schema.validate_schemas(return_schema=schema.StationsSchema)
    def _get_stations_geodataframe(
        self,
        stations: Collection[dict],
        filter_time_series: Collection[TimeSeriesProtocol] | None,
        excluded_stations: Collection[str] | None,
        station_name_key: str,
    ) -> gpd.GeoDataFrame:
        """
        Récupère les données des stations sous forme de GeoDataFrame.

        :param stations: Liste des stations.
        :type stations: Collection[dict]
        :param filter_time_series: Liste des séries temporelles pour filtrer les stations. Si None, toutes les stations sont retournées.
        :type filter_time_series: Collection[TimeSeriesProtocol] | None
        :param excluded_stations: Liste des stations à exclure.
        :type excluded_stations: Collection[str] | None
        :param station_name_key: Clé du nom de la station.
        :type station_name_key: str
        :return: Données des stations sous forme de GeoDataFrame.
        :rtype: gpd.GeoDataFrame[schema.StationsSchema]
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

        gdf_stations: gpd.GeoDataFrame[schema.StationsSchema] = gpd.GeoDataFrame(
            attributes, geometry=geometry, crs="EPSG:4326"
        ).astype(
            {
                schema_ids.ID: pd.StringDtype(),
                schema_ids.NAME: pd.StringDtype(),
                schema_ids.CODE: pd.StringDtype(),
            }
        )

        return gdf_stations

    @abstractmethod
    def get_stations_geodataframe(
        self,
        filter_time_series: Collection[TimeSeriesProtocol] | None,
        excluded_stations: Collection[str] | None = None,
        station_name_key: Optional[str] = "officialName",
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
        :rtype: gpd.GeoDataFrame[schema.StationsSchema]
        """
        ...

    @staticmethod
    @abstractmethod
    def _get_event_date(event: dict) -> datetime:
        """
        Récupère la date de l'événement.

        :param event: Données de l'événement.
        :type event: dict
        :return: Date de l'événement.
        :rtype: datetime
        """
        ...

    @staticmethod
    @abstractmethod
    def _get_qc_flag(event: dict) -> str:
        """
        Récupère le type du flag de qualité.

        :param event: Données de l'événement.
        :type event: dict
        :return: Type du flag de qualité.
        :rtype: str
        """
        ...

    def create_data_list(
        self, data: Collection[dict], time_serie_code: TimeSeriesProtocol
    ) -> list[dict]:
        """
        Crée une liste de données pour les séries temporelles.

        :param data: Données de la série temporelle.
        :type data: Collection[dict]
        :param time_serie_code: Le code de la série temporelle.
        :type time_serie_code: TimeSeriesProtocol
        :return: Liste des données.
        :rtype: list[dict]
        """
        return [
            {
                schema_ids.EVENT_DATE: self._get_event_date(event=event),
                schema_ids.VALUE: event["value"],
                schema_ids.TIME_SERIE_CODE: time_serie_code,
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

        :param data_dataframe: Données des séries temporelles sous forme de DataFrame.
        :type data_dataframe: pd.DataFrame
        :param time_serie_code: e code de la série temporelle des données.
        :type time_serie_code: TimeSeriesProtocol
        :param wlo_qc_flag_filter: Liste des flags de qualité à filtrer pour la série temporelle WLO.
        :type wlo_qc_flag_filter: Collection[str] | None
        :return: Données des séries temporelles sous forme de DataFrame.
        :rtype: pd.DataFrame
        """
        if time_serie_code == TimeSeriesProtocol.WLO:
            data_dataframe = (
                data_dataframe[~data_dataframe["qc_flag"].isin(wlo_qc_flag_filter)]
                if wlo_qc_flag_filter
                else data_dataframe
            )

        return data_dataframe

    @validate_schemas(return_schema=schema.WaterLevelSerieDataSchema)
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

        :param station: Code de la station.
        :type station: str
        :param from_time: La date de début en format ISO 8601 (ex: 2019-11-13T19:18:00Z).
        :type from_time: str
        :param to_time: La date de fin en format ISO 8601 (ex: 2019-11-13T19:18:00Z).
        :type to_time: str
        :param time_serie_code: Le code de la série temporelle désirée.
        :type time_serie_code: TimeSeriesProtocol
        :param time_delta: L'intervalle de temps maximale pour chaque requête.
        :type time_delta: timedelta
        :param datetime_sorted: Si les données doivent être triées par date.
        :type datetime_sorted: bool
        :param wlo_qc_flag_filter: Liste des flags de qualité à filtrer pour la série temporelle WLO.
        :type wlo_qc_flag_filter: Collection[str] | None
        :return: Données des séries temporelles sous forme de DataFrame.
        :rtype: pd.DataFrame[schema.WaterLevelSerieDataSchema]
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
                f"Aucune donnée de la série temporelle '{time_serie_code}' pour la station '{station}' "
                f"entre le {from_time} et le {to_time}."
            )
            return pd.DataFrame(
                columns=list(schema.WaterLevelSerieDataSchema.__annotations__.keys())
            )

        data_list: list[dict] = self.create_data_list(
            data=data.data, time_serie_code=time_serie_code  # type: ignore
        )

        data_dataframe: pd.DataFrame[schema.WaterLevelSerieDataSchema] = pd.DataFrame(
            data_list
        ).astype({schema_ids.TIME_SERIE_CODE: pd.StringDtype()})

        data_dataframe = self.filter_wlo_qc_flag(
            data_dataframe=data_dataframe,
            time_serie_code=time_serie_code,
            wlo_qc_flag_filter=wlo_qc_flag_filter,
        )

        data_dataframe.drop(columns=["qc_flag"], inplace=True)

        return data_dataframe
