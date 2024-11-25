import re
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta
from itertools import repeat
from typing import Any, Optional, Callable, Generator, Collection, Sequence

from cachetools.func import ttl_cache
from geopy import distance
from loguru import logger

from . import ids_iwls as ids
from .datetime_utils import split_time
from .endpoint import Endpoint, EndpointPrivateProd, EndpointPrivateDev, EndpointPublic
from .exceptions_iwls import CoordinatesError
from .models_api import Regions, TimeSeries, TypeTideTable
from ..handler.http_query_handler import HTTPQueryHandler, Response

LOGGER = logger.bind(name="IWLS.API")


class IWLSapiABC(ABC):
    __slots__ = (
        "_query_handler",
        "endpoint",
        "_cache",
    )

    def __init__(
        self,
        query_handler: HTTPQueryHandler,
        endpoint: EndpointPrivateDev | EndpointPrivateProd | EndpointPublic | Endpoint,
    ):
        self.endpoint = endpoint
        self._query_handler = query_handler

    @property
    @ttl_cache(ttl=300, maxsize=256)
    def _stations(self) -> list:
        return self.get_all_stations().data

    @property
    @ttl_cache(ttl=300, maxsize=256)
    def stations_list(self) -> list:
        return [station.get(ids.ID) for station in self._stations]

    @property
    @ttl_cache(ttl=300, maxsize=256)
    def stations_dict(self) -> dict:
        return {station.get(ids.ID): station for station in self._stations}

    @staticmethod
    def _validate_coordinates(
        latitude: float | int, longitude: float | int
    ) -> tuple[float | int, float | int]:
        """
        Méthode permettant de valider la latitude et la longitude.

        :param latitude: (Union[float, int]) La latitude de la station.
        :param longitude: (Union[float, int]) La longitude de la station.
        :return: (Tuple[Union[float, int], Union[float, int]]) La latitude et la longitude validées.
        :raise: TypeError si les coordonnées sont du mauvais type.
        :raise: CoordinatesError si les coordonnées sont invalides.
        """
        if not isinstance(latitude, (int, float)):
            raise TypeError("La latitude doit être de type 'int' ou 'float'.")

        if not isinstance(longitude, (int, float)):
            raise TypeError("La longitude doit être de type 'int' ou 'float'.")

        if not abs(latitude) <= 90:
            raise CoordinatesError("La latitude doit être comprise entre -90 et 90.")

        if not abs(longitude) <= 180:
            raise CoordinatesError("La longitude doit être comprise entre -180 et 180.")

        return latitude, longitude

    @staticmethod
    def _validate_iso_date(date: str) -> str:
        """
        Méthode permettant de valider le format de la date.

        :param date: (str) La date en format ISO 8601 UTC (ex: 2021-02-13T19:18:00Z).
        :return: (str) La date si est elle valide.
        :raise: ValueError si la date est invalide.
        """
        if not bool(re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", date)):
            raise ValueError(
                "La date doit être en format ISO 8601 UTC (ex: 2021-02-13T19:18:00Z)."
            )

        return date

    @ttl_cache(ttl=600, maxsize=256)
    def _validate_station_id(self, station_id: str) -> str:
        """
        Méthode permettant de valider l'identifiant d'une station'.

        :param station_id: (str) L'identifiant d'une station.
        :return: (str) L'identifiant si il est valide.
        :raise: ValueError si l'identifiant est invalide.
        """
        if not isinstance(station_id, str):
            raise TypeError("L'identifiant de la station doit être de type 'string'.")

        if len(station_id) != 24:
            raise ValueError(
                f"L'identifiant de la station ('stationId') doit contenir 24 caractères: {station_id}."
            )

        if self.stations_list is not None:
            if station_id not in self.stations_list:
                raise ValueError(
                    f"L'identifiant de la station ('stationId') est invalide: {station_id}."
                )

        return station_id

    def _validate_query_parameters(self, **kwargs) -> dict[str, str]:
        """
        Méthode permettant de valider les paramètres de la requête.

        :return: (dict[str, str]) Un dictionnaire contenant les paramètres valides.
        """
        query_params = {}
        for param in kwargs:
            if kwargs[param] is not None:
                if param == ids.FROM or param == ids.TO:
                    query_params[param] = self._validate_iso_date(kwargs[param])

                elif param == ids.TIME_SERIES_CODE:
                    if (
                        kwargs[param] in TimeSeries.get_values()
                        or kwargs[param] is None
                    ):
                        query_params[param] = kwargs[param]
                    else:
                        LOGGER.warning(
                            f"Le code de série temporelle '{kwargs[param]}' est invalide. "
                            f"Liste des choix valides : {', '.join(TimeSeries.get_values())}."
                        )

                elif param == ids.CHS_REGION_CODE:
                    if kwargs[param] in Regions.get_values() or kwargs[param] is None:
                        query_params[param] = kwargs[param]
                    else:
                        LOGGER.warning(
                            f"La région '{kwargs[param]}' est invalide. "
                            f"Liste des choix valides : {', '.join(Regions.get_values())}."
                        )

                elif param == ids.STATION:
                    query_params[param] = self._validate_station_id(kwargs[param])

                else:
                    query_params[param] = kwargs[param]

        return query_params

    def _construct_url(self, endpoint: str, **kwargs: str) -> str:
        """
        Méthode permettant de construire l'url de la requête.

        :param endpoint: (str) Un point d'entré pour la requête.
        :return: (str) L'url de la requête.
        """
        return self.endpoint.API + endpoint.format(**kwargs)

    def get_closest_station(
        self,
        stations_list: Collection[dict],
        latitude: float | int,
        longitude: float | int,
    ) -> dict[str, Any]:
        """
        Méthode permettant de récupérer la station la plus près des coordonnées géographiques.

        :param stations_list: (Collection[dict]) Une liste des stations.
        :param latitude: (Union[float, int]) La latitude en format degré décimal.
        :param longitude: (Union[float, int]) La longitude en format degré décimal.
        :return: (dict[str, Any]) Les informations de la station la plus près des coordonnées géographiques.
        """

        def station_distance(stations):
            """
            Méthode permettant de calculer la distance entre les coordonnées et une station.

            La formule de Vincenty est utilisée pour calculer la distance entre deux points sur la surface d'une sphère.
            """
            return distance.distance(
                (lat, long), (stations[ids.LATITUDE], stations[ids.LONGITUDE])
            )

        lat, long = self._validate_coordinates(latitude=latitude, longitude=longitude)
        closest_station = min(stations_list, key=station_distance)

        return closest_station

    @staticmethod
    def _aggregate_data(
        futures: Collection, time_serie_code: str, station: str
    ) -> tuple[list[dict], list[str]]:
        """
        Méthode permettant d'agréger les données de plusieurs requêtes.

        :param futures: (Collection) Une liste de futures contenant les données.
        :param time_serie_code: (str) Le code de la série temporelle.
        :param station: (str) L'identifiant de la station.
        :return: (tuple) Une liste de données agrégées et une liste d'erreurs.
        """
        data_aggregated = []
        errors = []

        for future in as_completed(futures):
            start, end, data = future.result()
            if data.is_ok:
                data_aggregated.extend(data.data)

            else:
                error: str = (
                    f"{data.message} - {data.error} "
                    f"MISSING DATA FROM {start} TO {end} FOR '{time_serie_code}' AT '{station}'"
                )
                errors.append(error)
                LOGGER.warning(f"Impossible de récupérer les données : {error}.")

        return data_aggregated, errors

    def _fetch_and_aggregate_data(
        self,
        function: Callable,
        interval: Generator[tuple[str, str], None, None],
        time_serie_code: str,
        station: str,
        datetime_sorted: bool = True,
    ) -> Response:
        """
        Méthode permettant de récupérer et d'agréger les données de plusieurs requêtes.

        :param function: (Callable) La fonction à exécuter.
        :param interval: (Generator) Un générateur contenant les intervalles de temps.
        :param time_serie_code: (str) Le code de la série temporelle.
        :param station: (str) L'identifiant de la station.
        :param datetime_sorted: (bool) Si les données doivent être triées par date.
        :return: (Response) Un objet Response contenant les données agrégées.
        """
        response = Response(status_code=200)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(function, start, end) for start, end in interval]
            data_aggregated, errors = self._aggregate_data(
                futures=futures, time_serie_code=time_serie_code, station=station
            )

        if data_aggregated:
            if datetime_sorted:
                data_aggregated.sort(
                    key=lambda x: x.get(ids.EVENT_DATE_EPOCH)
                    or x.get(ids.EVENT_DATE)
                    or x.get(ids.DATE_RECEIVED)
                )

            response.data = data_aggregated

        if errors:
            response.status_code = 400
            response.message = "MISSING DATA"
            response.error = errors

        return response

    def get_time_serie_block_data(
        self,
        station: str,
        from_time: str,
        to_time: str,
        time_serie_code: Optional[TimeSeries] = TimeSeries.WLO,
        time_delta: timedelta = timedelta(days=7),
        datetime_sorted: bool = True,
        **kwargs,
    ) -> Response:
        """
        Méthode permttant de récupérer des données à partir de l'API de iWLS.

            /api/v1/stations/{stationId}/data

        :param station: (str) Le stationId de la station.
        :param time_serie_code: (TimeSeries) Le code de la série temporelle désirée.
                                    wlo : Official quality controlled water level observation
                                    wlp: Water level prediction for the next years
                                    wlp-hilo: Tide tables prediction for the next years
                                    wlp-bores : Bores arrival and intensity
                                    wcp-slack : Reversing falls
                                    wlf : Water level forecast for the next 48 hours
                                    wlf-spine
                                    dvcf-spine : Dynamic vertical clearance forecast under infrastructure like bridges
        :param from_time: (str) La date de début en format ISO 8601 (ex: 2019-11-13T19:18:00Z).
        :param to_time: (str) La date de fin en format ISO 8601 (ex: 2019-11-13T19:18:00Z).
        :param time_delta: (timedelta) L'intervalle de temps maximale pour chaque requête.
        :param datetime_sorted: (bool) Si les données doivent être triées par date.
        :return: (Response) Un objet Response contenant les données reçues de l'API de iWLS.
        """

        def fetch_data(start: str, end: str) -> tuple[str, str, Response]:
            data: Response = self.get_time_serie_data(
                station=station,
                from_time=start,
                to_time=end,
                time_serie_code=time_serie_code,
                **kwargs,
            )
            return start, end, data

        interval: Generator[tuple[str, str], None, None] = split_time(
            from_time=from_time,
            to_time=to_time,
            time_delta=time_delta,
        )

        return self._fetch_and_aggregate_data(
            function=fetch_data,
            interval=interval,
            time_serie_code=time_serie_code,
            station=station,
            datetime_sorted=datetime_sorted,
        )

    @abstractmethod
    def get_time_serie_data(
        self,
        station: str,
        from_time: str,
        to_time: str,
        time_serie_code: Optional[TimeSeries] = TimeSeries.WLO,
        **kwargs,
    ) -> Response:
        """
        Méthode permttant de récupérer des données à partir de l'API de iWLS.

        :param station: (str) Le stationId de la station.
        :param time_serie_code: (TimeSerie) Le code de la série temporelle désirée.
                                    wlo : Official quality controlled water level observation
                                    wlp: Water level prediction for the next years
                                    wlp-hilo: Tide tables prediction for the next years
                                    wlp-bores : Bores arrival and intensity
                                    wcp-slack : Reversing falls
                                    wlf : Water level forecast for the next 48 hours
                                    wlf-spine
                                    dvcf-spine : Dynamic vertical clearance forecast under infrastructure like bridges
                                    ...
        :param from_time: (str) La date de début en format ISO 8601 (ex: 2019-11-13T19:18:00Z).
        :param to_time: (str) La date de fin en format ISO 8601 (ex: 2019-11-13T19:18:00Z).
        :return: (Response) Un objet Response contenant les données de la série temporelle.
        """
        ...

    def get_time_series_data(
        self,
        time_series: Sequence[TimeSeries],
        station: str,
        from_time: str,
        to_time: str,
        time_delta: timedelta = timedelta(days=7),
        datetime_sorted: bool = True,
    ) -> dict[TimeSeries, Response]:
        """
        Méthode permettant de récupérer plusieurs série temporelle pour une station sur l'API de iWLS.

        :param time_series: (Sequence[TimeSeries]) La liste des codes des times série.
        :param station: (str) Le code de la station.
        :param from_time: (str) La date de début en format ISO 8601 UTC (ex: 2021-02-13T19:18:00Z).
        :param to_time: (str) La date de fin en format ISO 8601 UTC (ex: 2021-02-13T19:18:00Z).
        :param time_delta: (timedelta) L'intervalle de temps maximale pour chaque requête.
        :param datetime_sorted: (bool) Si les données doivent être triées par date.
        :return: dict[TimeSeries, Response] Les résultats de la requête.
        """
        with ThreadPoolExecutor() as executor:
            results = {
                time_series[index]: result
                for index, result in enumerate(
                    executor.map(
                        self.get_time_serie_block_data,
                        repeat(station),
                        repeat(from_time),
                        repeat(to_time),
                        time_series,
                        repeat(time_delta),
                        repeat(datetime_sorted),
                    )
                )
            }

        return results

    @abstractmethod
    def get_info_station(self, station: str) -> Response:
        """
        Méthode permettant de récupérer les informations concernant une station.

        :param station: (str) L'identifiant de la station.
        :return: (Response) Un objet Response contenant les informations de la station.
        """
        ...

    @abstractmethod
    def get_metadata_station(self, station: str) -> Response:
        """
        Méthode permettant de récupérer les métadonnées concernant une station.

        :param station: (str) Le stationId de la station.
        :return: (Response) Un objet Response contenant les métadonnées de la station.
        """
        ...

    def get_metadata_stations(self, stations: Sequence[str]) -> dict[str, Response]:
        """
        Méthode permettant de récupérer les métadonnées concernant une liste de stations.

        :param stations: (Sequence[str]) Une liste contenant le stationId des station.
        :return: (dict[str, Response]) Un objet Response contenant les métadonnées des stations.
        """
        with ThreadPoolExecutor() as executor:
            results = {
                stations[index]: result
                for index, result in enumerate(
                    executor.map(self.get_metadata_station, stations)
                )
            }

        return results

    @abstractmethod
    def get_all_stations(
        self,
        code: Optional[str] = None,
        chs_region_code: Optional[Regions] = None,
        time_serie_code: Optional[TimeSeries] = None,
    ) -> Response:
        """
        Méthode permettant de récupérer une liste de stations ainsi que les informations les concernant.

        :param code: (str) Le code d'une station. Écrase les autres paramètres.
        :param chs_region_code: (Regions) Le code d'une région (PAC, CNA, ATL, QUE).
        :param time_serie_code: (TimeSeries) Le code de la série temporelle désirée.
                                    wlo : Official quality controlled water level observation
                                    wlp: Water level prediction for the next years
                                    wlp-hilo: Tide tables prediction for the next years
                                    wlp-bores : Bores arrival and intensity
                                    wcp-slack : Reversing falls
                                    wlf : Water level forecast for the next 48 hours
                                    wlf-spine
                                    dvcf-spine : Dynamic vertical clearance forecast under infrastructure like bridges
        :return: (Response) Un objet Response contenant les stations ainsi que les informations les concernant.
        """
        ...

    @abstractmethod
    def get_height_types(self) -> Response:
        """
        Méthode permettant de récupérer les types de hauteur.

        :return: (Response) Un objet Response contenant les différents types de hauteur.
        """
        ...

    @abstractmethod
    def get_height(self, height: str) -> Response:
        """
        Méthode permettant de récupérer un type de hauteur.

        :param height: (str) L'identifiant de la hauteur.
        :return: (Response) Un objet Response contenant les informations concernant ce type de hauteur.
        """
        ...

    @abstractmethod
    def get_station_montly_mean(
        self, station: str, year: str, month: str, **kwargs
    ) -> Response:
        """
        Méthode permettant d'obtenir la moyenne mensuelle pour une station.

        :param station: (str) Le stationId de la station.
        :param year: (str) L'année désirée.
        :param month: (str) Le mois désiré.
        :return: (Response) La moyenne mensuelle de la station.
        """
        ...

    @abstractmethod
    def get_station_daily_mean(
        self, station: str, from_time: str, to_time: str, **kwargs
    ) -> Response:
        """
        Méthode permettant d'obtenir les moyennes journalières pour une station.

        :param station: (str) Le stationId de la station.
        :param from_time: (str) La date de début en format (ex: 2019-11-13).
        :param to_time: (str) La date de fin en format (ex: 2019-11-13).
        :return: (Response) Un objet Response contenant les moyenne journalières de la station.
        """
        ...

    @abstractmethod
    def get_phenomena(self) -> Response:
        """
        Méthode permettant de récupérer les phénomènes.

        :return: (Response) Un objet Response contenant les différents phénomènes.
        """
        ...

    @abstractmethod
    def get_phenomenon(self, phenomenon: str) -> Response:
        """
        Méthode permettant de récupérer les informations d'un phénomène.

        :return: (Response) Un objet Response contenant les informations concernant un phénomène.
        """
        ...

    @abstractmethod
    def get_tide_tables(
        self, type_table: TypeTideTable = None, parent_tide_table: str = None
    ) -> Response:
        """
        Méthode permettant de recupérer la liste des tables de marées.

        :param type_table: (TypeTideTable) Un type de table. {VOLUME, AREA, SUB_AREA}
        :param parent_tide_table: (str) L'identifiant d'une table.
        :return: (Response) Un objet Response contenant l'ensemble des tables de marées correspondant
                            aux critères de la recherche.
        """
        ...

    @abstractmethod
    def get_tide_table(self, tide_table: str) -> Response:
        """
        Méthode permettant de recupérer une table de marées.

        :param tide_table: (str) L'identifiant d'une table de marées.
        :return: (Response) Un objet Response contenant les informations d'une table de marées.
        """
        ...

    @abstractmethod
    def get_time_series_definitions(
        self, time_serie: Optional[TimeSeries] = None
    ) -> Response:
        """
        Méthode permettant de récupérer les définitions des séries temporelles.

        :param time_serie: (TimeSeries) Le code de la série temporelle.
        :return: (Response) Un objet Response contenant les définitions des séries temporelles.
        """
        ...

    @abstractmethod
    def get_time_serie_definition(self, time_serie_definition_id: str) -> Response:
        """
        Méthode permettant de récupérer la définition d'une série temporelle.

        :param time_serie_definition_id: (str) L'identifiant de la série temporelle.
        :return: (Response) Un objet Response contenant la définition de la série temporelle.
        """
        ...

    @abstractmethod
    def get_benchmarks(self, station_ids: Collection[str] = None, **kwargs) -> Response:
        """
        Méthode permettant de récupérer les repères des stations.

        :param station_ids: (Collection[str]) Une liste contenant les identifiants des stations.
        :return: (Response) Un objet Response contenant les informations sur les repères.
        """
        ...

    @abstractmethod
    def get_benchmark(self, benchmark_id: str) -> Response:
        """
        Méthode permettant de récupérer un repère.

        :param benchmark_id: (str) L'identifiant du repère.
        :return: (Response) Un objet Response contenant les informations sur le repère.
        """
        ...

    @abstractmethod
    def get_benchmark_metadata(self, benchmark_id: str) -> Response:
        """
        Méthode permettant de récupérer les métadonnées d'un repère.

        :param benchmark_id: (str) L'identifiant du repère.
        :return: (Response) Un objet Response contenant les métadonnées sur le repère.
        """
        ...

    @abstractmethod
    def get_elevations(self, benchmark_id: str) -> Response:
        """
        Méthode permettant de récupérer les métadonnées d'un repère.

        :param benchmark_id: (str) L'identifiant du repère.
        :return: (Response) Un objet Response contenant les métadonnées sur le repère.
        """

    def get_elevations_for_benchmarks(
        self, benchmarks_ids: Sequence[str] = None
    ) -> dict[str, Response]:
        """
        Méthode permettant de récupérer les élévations concernant une liste de repères.

        :param benchmarks_ids: (Sequence[str]) Une liste contenant les benchmarks.
        :return: (dict[str, Response]) Un objet Response contenant les élévations des repères.
        """
        with ThreadPoolExecutor() as executor:
            results = {
                benchmarks_ids[index]: result
                for index, result in enumerate(
                    executor.map(self.get_elevations, benchmarks_ids)
                )
            }

        return results

    def get_metadata_for_benchmarks(
        self, benchmarks_ids: Sequence[str] = None
    ) -> dict[str, Response]:
        """
        Méthode permettant de récupérer les métadonnées concernant une liste de repères.

        :param benchmarks_ids: (Sequence[str]) Une liste contenant les benchmarks.
        :return: (dict[str, Response]) Un objet Response contenant les métadonnées des repères.
        """
        with ThreadPoolExecutor() as executor:
            results = {
                benchmarks_ids[index]: result
                for index, result in enumerate(
                    executor.map(self.get_benchmark_metadata, benchmarks_ids)
                )
            }

        return results
